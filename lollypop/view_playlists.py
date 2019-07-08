# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GLib

from random import shuffle

from lollypop.utils import get_human_duration, tracks_to_albums
from lollypop.view import LazyLoadingView
from lollypop.define import App, Type, ViewType, SidebarContent, MARGIN
from lollypop.objects import Album, Track
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_playlist_banner import PlaylistBannerWidget
from lollypop.view_albums_list import AlbumsListView


class PlaylistsView(LazyLoadingView, ViewController):
    """
        Show playlist tracks
    """

    def __init__(self, playlist_ids, view_type):
        """
            Init PlaylistView
            @parma playlist ids as [int]
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__playlist_ids = playlist_ids
        self.__signal_id1 = App().playlists.connect(
                                            "playlist-track-added",
                                            self.__on_playlist_track_added)
        self.__signal_id2 = App().playlists.connect(
                                            "playlist-track-removed",
                                            self.__on_playlist_track_removed)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistView.ui")
        self.__title_label = builder.get_object("title")
        self.__duration_label = builder.get_object("duration")
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        self.__jump_button = builder.get_object("jump_button")
        self.__menu_button = builder.get_object("menu_button")
        self.__buttons = builder.get_object("box-buttons")
        self.__widget = builder.get_object("widget")
        # We remove SCROLLED because we want to be the scrolled view
        self.__view = AlbumsListView([], [], view_type & ~ViewType.SCROLLED)
        self.__view.connect("remove-from-playlist",
                            self.__on_remove_from_playlist)
        self.__view.show()
        self.__title_label.set_margin_start(MARGIN)
        self.__buttons.set_margin_end(MARGIN)
        self.__duration_label.set_margin_start(MARGIN)
        self._overlay = Gtk.Overlay.new()
        if view_type & ViewType.SCROLLED:
            self._viewport.add(self.__view)
            self._overlay.add(self._scrolled)
        else:
            self._overlay.Add(self._view)
        self._overlay.show()
        self.__widget.attach(self.__title_label, 0, 0, 1, 1)
        self.__widget.attach(self.__duration_label, 0, 1, 1, 1)
        self.__widget.attach(self.__buttons, 1, 0, 1, 2)
        self.__widget.set_vexpand(True)
        self.__title_label.set_vexpand(True)
        self.__duration_label.set_vexpand(True)
        self.__title_label.set_property("valign", Gtk.Align.END)
        self.__duration_label.set_property("valign", Gtk.Align.START)
        self.__banner = PlaylistBannerWidget(playlist_ids[0], view_type)
        self.__banner.show()
        self._overlay.add_overlay(self.__banner)
        self.__banner.add_overlay(self.__widget)
        self.__view.set_margin_top(self.__banner.default_height)
        self.add(self._overlay)
        self.__title_label.set_label(
            ", ".join(App().playlists.get_names(playlist_ids)))
        builder.connect_signals(self)

        if len(playlist_ids) > 1:
            self.__menu_button.hide()

        self.set_view_type(view_type)

        # In DB duration calculation
        if playlist_ids[0] > 0 and\
                not App().playlists.get_smart(playlist_ids[0]):
            duration = 0
            for playlist_id in self.__playlist_ids:
                duration += App().playlists.get_duration(playlist_id)
            self.__set_duration(duration)
        # Ask widget after populated
        else:
            self.__view.connect("populated", self.__on_playlist_populated)

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        def update_button(button, style, icon_size, icon_name):
            context = button.get_style_context()
            context.remove_class("menu-button-48")
            context.remove_class("menu-button")
            context.add_class(style)
            button.get_image().set_from_icon_name(icon_name, icon_size)

        self.__banner.set_view_type(view_type)
        self._view_type = view_type
        if view_type & ViewType.SMALL:
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__duration_label.get_style_context().add_class(
                "text-large")
        else:
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
            self.__duration_label.get_style_context().add_class(
                "text-x-large")
        update_button(self.__play_button, style,
                      icon_size, "media-playback-start-symbolic")
        update_button(self.__shuffle_button, style,
                      icon_size, "media-playlist-shuffle-symbolic")
        update_button(self.__jump_button, style,
                      icon_size, "go-jump-symbolic")
        update_button(self.__menu_button, style,
                      icon_size, "view-more-symbolic")

    def populate(self, albums):
        """
            Populate view with albums
            @param albums as [Album]
        """
        self.__view.populate(albums)

    def stop(self):
        """
            Stop populating
        """
        self.__view.stop()

    @property
    def playlist_ids(self):
        """
            Return playlist ids
            @return id as [int]
        """
        return self.__playlist_ids

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Adapt widget to current scroll value
            @param adj as Gtk.Adjustment
        """
        LazyLoadingView._on_value_changed(self, adj)
        if not self._view_type & (ViewType.POPOVER | ViewType.FULLSCREEN):
            title_style_context = self.__title_label.get_style_context()
            if adj.get_value() == adj.get_lower():
                height = self.__banner.default_height
                self.__duration_label.show()
                self.__title_label.set_property("valign", Gtk.Align.END)
                if not App().window.is_adaptive:
                    title_style_context.remove_class("text-x-large")
                    title_style_context.add_class("text-xx-large")
            else:
                self.__duration_label.hide()
                title_style_context.remove_class("text-xx-large")
                title_style_context.add_class("text-x-large")
                self.__title_label.set_property("valign", Gtk.Align.CENTER)
                height = self.__banner.default_height // 3
            # Make grid cover artwork
            # No idea why...
            self.__banner.set_height(height)
            self.__widget.set_size_request(-1, height + 1)

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.__update_jump_button()

    def _on_destroy(self, widget):
        """
            Disconnect signals
            @param widget as Gtk.Widget
        """
        LazyLoadingView._on_destroy(self, widget)
        if self.__signal_id1:
            App().playlists.disconnect(self.__signal_id1)
            self.__signal_id1 = None
        if self.__signal_id2:
            App().playlists.disconnect(self.__signal_id2)
            self.__signal_id2 = None

    def _on_jump_button_clicked(self, button):
        """
            Scroll to current track
            @param button as Gtk.Button
        """
        self.__view.jump_to_current(self._scrolled)

    def _on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self.__view.children:
            for track_row in album_row.children:
                tracks.append(track_row.track)
        if tracks:
            albums = tracks_to_albums(tracks)
            App().player.play_albums(albums, tracks[0])

    def _on_shuffle_button_clicked(self, button):
        """
            Play playlist shuffled
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self.__view.children:
            for track_row in album_row.children:
                tracks.append(track_row.track)
        if tracks:
            shuffle(tracks)
            albums = tracks_to_albums(tracks)
            App().player.play_albums(albums, tracks[0])

    def _on_menu_button_clicked(self, button):
        """
            Show playlist menu
            @param button as Gtk.Button
        """
        from lollypop.menu_playlist import PlaylistMenu
        menu = PlaylistMenu(self.__playlist_ids[0])
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

    def _on_map(self, widget):
        """
            Set active ids
        """
        sidebar_content = App().settings.get_enum("sidebar-content")
        if sidebar_content != SidebarContent.GENRES:
            App().window.emit("show-can-go-back", True)
            App().window.emit("can-go-back-changed", True)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.PLAYLISTS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self.__playlist_ids))
        App().settings.set_value("state-three-ids",
                                 GLib.Variant("ai", []))

    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        if status:
            view_type = self._view_type | ViewType.SMALL
        else:
            view_type = self._view_type & ~ViewType.SMALL
        self.set_view_type(view_type)

#######################
# PRIVATE             #
#######################
    def __set_duration(self, duration):
        """
            Set playlist duration
            @param duration as int (seconds)
        """
        self.__duration_label.set_text(get_human_duration(duration))

    def __update_jump_button(self):
        """
            Update jump button status
        """
        track_ids = []
        for child in self.__view.children:
            track_ids += child.album.track_ids
        if App().player.current_track.id in track_ids:
            self.__jump_button.set_sensitive(True)
        else:
            self.__jump_button.set_sensitive(False)

    def __on_populated(self, playlists_widget):
        """
            Update jump button on populated
            @param playlists_widget as PlaylistsWidget
        """
        self.__update_jump_button()

    def __on_playlist_track_added(self, playlists, playlist_id, uri):
        """
            Append track to album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track = Track(App().tracks.get_id_by_uri(uri))
            album = Album(track.album.id)
            album.set_tracks([track])
            self.__view.insert_album(album, True, -1)

    def __on_playlist_track_removed(self, playlists, playlist_id, uri):
        """
            Remove track from album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if len(self.__playlist_ids) == 1 and\
                playlist_id in self.__playlist_ids:
            track = Track(App().tracks.get_id_by_uri(uri))
            children = self.__view.children
            for album_row in children:
                if album_row.album.id == track.album.id:
                    for track_row in album_row.children:
                        if track_row.track.id == track.id:
                            track_row.destroy()
                            if len(children) == 1:
                                album_row.destroy()
                                break

    def __on_remove_from_playlist(self, view, object):
        """
            Remove object from playlist
            @param view as AlbumListView
            @param object as Album/Track
        """
        if isinstance(object, Album):
            tracks = object.tracks
        else:
            tracks = [object]
        App().playlists.remove_tracks(self.__playlist_ids[0], tracks)

    def __on_playlist_populated(self, widget):
        """
            Set duration on populated
            @param widget as PlaylistsWidget
        """
        self.__set_duration(widget.duration)
