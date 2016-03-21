# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Pango

from gettext import gettext as _

from lollypop.define import Lp, ArtSize, Type
from lollypop.objects import Track
from lollypop.widgets_album import AlbumWidget
from lollypop.pop_radio import RadioPopover


class RadioWidget(Gtk.Frame, AlbumWidget):
    """
        Widget with radio cover and title
    """

    def __init__(self, name, radios_manager):
        """
            Init radio widget
            @param name as string
            @param radios_manager as RadiosManager
        """
        Gtk.Frame.__init__(self)
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self.get_style_context().add_class('loading')
        self._name = name
        self._cover = None
        self._radios_manager = radios_manager

    def populate(self):
        """
            Init widget content
        """
        self.get_style_context().remove_class('loading')
        AlbumWidget.__init__(self, None)
        self._widget = Gtk.EventBox()
        self._widget.connect('enter-notify-event', self._on_enter_notify)
        self._widget.connect('leave-notify-event', self._on_leave_notify)
        self._cover = Gtk.Image()
        self._cover.get_style_context().add_class('cover-frame')
        self._cover.set_property('halign', Gtk.Align.CENTER)
        self._cover.set_size_request(ArtSize.BIG, ArtSize.BIG)
        self._cover.get_style_context().add_class('white')
        self._title_label = Gtk.Label()
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label.set_property('halign', Gtk.Align.CENTER)
        self._title_label.set_text(self._name)
        overlay = Gtk.Overlay.new()
        overlay.get_style_context().add_class('white')
        # Play button
        play_event = Gtk.EventBox()
        play_event.set_property('has-tooltip', True)
        play_event.set_tooltip_text(_("Play"))
        play_event.set_hexpand(True)
        play_event.set_property('valign', Gtk.Align.CENTER)
        play_event.set_property('halign', Gtk.Align.CENTER)
        play_event.connect('realize', self._on_eventbox_realize)
        play_event.connect('button-press-event',
                           self._on_play_press_event)
        self._play_button = Gtk.Image.new_from_icon_name(
                                           'media-playback-start-symbolic',
                                           Gtk.IconSize.DND)
        self._play_button.set_opacity(0)
        # Edit button
        edit_event = Gtk.EventBox()
        edit_event.set_property('has-tooltip', True)
        edit_event.set_tooltip_text(_("Change artwork"))
        edit_event.set_property('halign', Gtk.Align.END)
        edit_event.connect('realize', self._on_eventbox_realize)
        edit_event.connect('button-press-event',
                           self._on_edit_press_event)
        edit_event.set_property('valign', Gtk.Align.END)
        edit_event.set_property('halign', Gtk.Align.END)
        self._edit_button = Gtk.Image.new_from_icon_name(
                                           'document-properties-symbolic',
                                           Gtk.IconSize.BUTTON)
        self._edit_button.set_opacity(0)
        overlay.add(self._cover)
        overlay.add_overlay(play_event)
        overlay.add_overlay(edit_event)
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.add(overlay)
        grid.add(self._title_label)
        self._widget.add(grid)
        self._widget.set_property('halign', Gtk.Align.CENTER)
        self._widget.set_property('valign', Gtk.Align.CENTER)
        self.add(self._widget)
        self.set_cover()
        self.update_state()
        self.show_all()
        play_event.add(self._play_button)
        edit_event.add(self._edit_button)

    def set_sensitive(self, b):
        """
            Ignore set sensitive
        """
        pass

    def get_id(self):
        """
            Return widget id (same value for all radio widgets)
        """
        return Type.RADIOS

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._cover is not None:
            widths = self._cover.get_preferred_width()
            return (widths[0] + 8, widths[1] + 8)
        else:
            return (0, 0)

    def set_name(self, name):
        """
            Set radio name
            @param name as string
        """
        self._name = name
        self._title_label.set_label(name)

    def get_name(self):
        """
            Return radio name
            @return name as string
        """
        return self._name

    def set_cover(self):
        """
            Set cover for album if state changed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_radio_artwork(
                    self._name,
                    ArtSize.BIG*self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        del surface

    def update_cover(self):
        """
            Update cover for radio
        """
        if self._cover is None:
            return
        surface = Lp().art.get_radio_artwork(
                    self._name,
                    ArtSize.BIG*self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        del surface

    def update_state(self):
        """
            Update widget state
        """
        if self._cover is None:
            return
        selected = Lp().player.current_track.id == Type.RADIOS and\
            self._name == Lp().player.current_track.album_artist
        if selected:
            self._cover.get_style_context().add_class(
                                                    'cover-frame-selected')
        else:
            self._cover.get_style_context().remove_class(
                                                    'cover-frame-selected')

#######################
# PRIVATE             #
#######################
    def _on_enter_notify(self, widget, event):
        """
            Show special buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        if self._play_button.get_opacity() == 0:
            self._cover.get_style_context().add_class('hovereffect')
            self._play_button.set_opacity(1)
            self._play_button.get_style_context().add_class(
                                                           self._rounded_class)
            self._play_button.show()
            self._edit_button.set_opacity(1)
            self._edit_button.get_style_context().add_class(
                                                           self._squared_class)
            self._edit_button.show()

    def _on_pop_cover_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self._popover = False
        self._play_button.set_opacity(0)
        self._play_button.get_style_context().remove_class(self._rounded_class)
        self._edit_button.set_opacity(0)
        self._edit_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _on_leave_notify(self, widget, event):
        """
            Hide special buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x < 5 or\
           event.x > allocation.width - 5 or\
           event.y < 5 or\
           event.y > allocation.height - 5:
            self._cover.get_style_context().remove_class('hovereffect')
            self._play_button.set_opacity(0)
            self._play_button.hide()
            self._play_button.get_style_context().remove_class(
                                                           self._rounded_class)
            self._edit_button.hide()
            self._edit_button.set_opacity(0)
            self._edit_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _on_play_press_event(self, widget, event):
        """
            Play radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        url = self._radios_manager.get_url(self._name)
        if url:
            track = Track()
            track.set_radio(self._name, url)
            Lp().player.load(track)

    def _on_edit_press_event(self, widget, event):
        """
            Edit radio
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        self._popover = True
        popover = RadioPopover(self._name, self._radios_manager)
        popover.set_relative_to(widget)
        popover.connect('closed', self._on_pop_cover_closed)
        popover.show()
