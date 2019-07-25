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

from gi.repository import Gtk

from gettext import gettext as _

from lollypop.view import View
from lollypop.utils import get_network_available
from lollypop.define import ViewType, StorageType
from lollypop.helper_filtering import FilteringHelper
from lollypop.view_albums_box import AlbumsPopularsBoxView
from lollypop.view_albums_box import AlbumsRandomGenreBoxView
from lollypop.view_artists_rounded import RoundedArtistsRandomView


class HomeView(View, FilteringHelper):
    """
        View showing information about use collection
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, view_type)
        FilteringHelper.__init__(self)
        self.__grid = Gtk.Grid()
        self.__grid.set_row_spacing(5)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()
        self._viewport.add(self.__grid)
        if view_type & ViewType.SCROLLED:
            self._viewport.set_property("valign", Gtk.Align.START)
            self._scrolled.set_property("expand", True)
            self.add(self._scrolled)

    def populate(self):
        """
            Populate view
        """
        for _class in [AlbumsPopularsBoxView,
                       RoundedArtistsRandomView,
                       AlbumsRandomGenreBoxView]:
            view = _class(self._view_type)
            view.populate()
            view.show()
            self.__grid.add(view)
        if get_network_available("SPOTIFY") and\
                get_network_available("YOUTUBE"):
            from lollypop.view_albums_box import AlbumsSpotifyBoxView
            spotify_view = AlbumsSpotifyBoxView(_("You should like this:"),
                                                self._view_type)
            spotify_view.populate(StorageType.SPOTIFY_SIMILARS)
            self.__grid.add(spotify_view)
            spotify_view = AlbumsSpotifyBoxView(_("New albums from Spotify"),
                                                self._view_type)
            spotify_view.populate(StorageType.SPOTIFY_NEW_RELEASES)
            self.__grid.add(spotify_view)

    def activate_child(self):
        """
            Activated typeahead row
        """
        for child in reversed(self.__grid.get_children()):
            child._box.unselect_all()
        for row in self.filtered:
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                row.activate()
            style_context.remove_class("typeahead")

    @property
    def filtered(self):
        """
            Get filtered widgets
            @return [Gtk.Widget]
        """
        children = []
        for child in reversed(self.__grid.get_children()):
            children += child.children
        return children

    @property
    def scroll_relative_to(self):
        """
            Relative to scrolled widget
            @return Gtk.Widget
        """
        return self

    @property
    def view_sizing_mask(self):
        """
            Get mask for adaptive mode
            @return ViewType
        """
        return ViewType.MEDIUM

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"view_type": view_type}, self._sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        pass
