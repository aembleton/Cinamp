# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gdk, GLib
from gettext import gettext as _

from lollypop.thirdparty.GioNotify import GioNotify

from lollypop.define import App, ArtSize, Type
from lollypop.utils import is_gnome


class NotificationManager:
    """
        Freedesktop notification support
    """

    def __init__(self):
        """
            Init notification object with lollypop infos
        """
        self.__supports_actions = False
        self.__disable_all_notifications = True
        self.__is_gnome = is_gnome()
        self.__notification = None
        self.__notification_handler_id = None
        GioNotify.async_init("Lollypop",
                             self.__on_init_finish)

    def send(self, message, sub=""):
        """
            Send message to user
            @param message as str
            @param sub as str
        """

        if self.__disable_all_notifications:
            return

        if self.__supports_actions:
            self.__notification.clear_actions()

        self.__notification.show_new(
            message,
            sub,
            "org.gnome.Lollypop-symbolic",
        )

        if self.__supports_actions:
            self.__set_actions()

#######################
# PRIVATE             #
#######################

    def __on_init_finish(self, notification, server_info, caps, error=None):
        """
            Set actions and connect signals
            @param notification as GioNotify
            @param server_info as {}
            @param caps as [str]
        """
        if error is not None:
            print("notification::__on_init_finish():", error)
            return

        self.__notification = notification

        self.__notification.set_hint(
            "category",
            GLib.Variant("s", "x-gnome.music"),
        )

        self.__notification.set_hint(
            "desktop-entry",
            GLib.Variant("s", "org.gnome.Lollypop"),
        )

        if "action-icons" in caps:
            self.__notification.set_hint(
                "action-icons",
                GLib.Variant("b", True),
            )

        if "persistence" in caps:
            self.__notification.set_hint(
                "transient",
                GLib.Variant("b", True),
            )

        if "actions" in caps:
            self.__supports_actions = True
            self.__set_actions()

        self.__on_notifications_settings_changed()

        App().settings.connect(
            "changed::disable-song-notifications",
            self.__on_notifications_settings_changed,
        )

        App().settings.connect(
            "changed::disable-notifications",
            self.__on_notifications_settings_changed,
        )

    def __set_actions(self):
        """
            Set notification actions
        """

        self.__notification.add_action(
            "media-skip-backward",
            _("Previous"),
            App().player.prev,
        )

        self.__notification.add_action(
            "media-skip-forward",
            _("Next"),
            App().player.next,
        )

    def __on_current_changed(self, player):
        """
            Send notification with track_id infos
            @param player Player
        """
        state = App().window.get_window().get_state()
        if player.current_track.id is None or\
                state & Gdk.WindowState.FOCUSED or\
                App().is_fullscreen():
            return
        # Since GNOME 3.24, using album cover looks bad
        if self.__is_gnome:
            cover_path = "org.gnome.Lollypop-symbolic"
        else:
            if player.current_track.id == Type.RADIOS:
                cover_path = App().art.get_radio_cache_path(
                    player.current_track.album_artists[0], ArtSize.BIG)
            else:
                cover_path = App().art.get_album_cache_path(
                    player.current_track.album, ArtSize.BIG)
            if cover_path is None:
                cover_path = "org.gnome.Lollypop-symbolic"

        if player.current_track.album.name == "":
            self.__notification.show_new(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                _("by %s") %
                "<b>" + ", ".join(player.current_track.artists) + "</b>",
                cover_path)
        else:
            self.__notification.show_new(
                player.current_track.title,
                # TRANSLATORS: by refers to the artist,
                # from to the album
                _("by %s, from %s") %
                ("<b>" + ", ".join(player.current_track.artists) + "</b>",
                 "<i>" + player.current_track.album.name + "</i>"),
                cover_path)

    def __on_notifications_settings_changed(self, *ignore):
        self.__disable_all_notifications = App().settings.get_value(
            "disable-notifications",
        )

        disable_song_notifications = App().settings.get_value(
            "disable-song-notifications",
        )

        if self.__notification_handler_id:
            App().player.disconnect(self.__notification_handler_id)
            self.__notification_handler_id = None

        if (not self.__disable_all_notifications and not
                disable_song_notifications):
            self.__notification_handler_id = App().player.connect(
                "current-changed",
                self.__on_current_changed,
            )
