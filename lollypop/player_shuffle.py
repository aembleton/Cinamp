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

import random

from lollypop.define import Shuffle, Repeat, App
from lollypop.player_base import BasePlayer
from lollypop.objects_track import Track
from lollypop.objects_radio import Radio
from lollypop.objects_album import Album
from lollypop.list import LinkedList
from lollypop.logger import Logger


class ShufflePlayer(BasePlayer):
    """
        Shuffle player
        Manage shuffle tracks and party mode
    """

    def __init__(self):
        """
            Init shuffle player
        """
        BasePlayer.__init__(self)
        # Party mode
        self.__is_party = False
        self.reset_history()
        App().settings.connect("changed::shuffle", self.__set_shuffle)

    def reset_history(self):
        """
            Reset history
        """
        # Tracks already played
        self.__history = []
        # Albums already played
        self.__already_played_albums = []
        # Tracks already played for albums
        self.__already_played_tracks = {}

    def next(self):
        """
            Next shuffle track
            @return Track
        """
        repeat = App().settings.get_enum("repeat")
        if repeat == Repeat.TRACK:
            return self._current_playback_track
        track = Track()
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_next:
                track = self.__history.next.value
            elif self._albums:
                track = self.__get_next()
        return track

    def prev(self):
        """
            Prev track based on history
            @return Track
        """
        repeat = App().settings.get_enum("repeat")
        if repeat == Repeat.TRACK:
            return self._current_playback_track
        track = Track()
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.shuffle_has_prev:
                track = self.__history.prev.value
            else:
                track = self._current_playback_track
        return track

    def set_party(self, party):
        """
            Set party mode on if party is True
            Play a new random track if not already playing
            @param party as bool
        """
        if party == self.__is_party:
            return
        self.__is_party = party
        self.reset_history()

        if self._plugins1.rgvolume is not None and\
           self._plugins2.rgvolume is not None:
            if party:
                self._plugins1.rgvolume.props.album_mode = 0
                self._plugins2.rgvolume.props.album_mode = 0
            else:
                self._plugins1.rgvolume.props.album_mode = 1
                self._plugins2.rgvolume.props.album_mode = 1

        if party:
            self.set_party_ids()
            if self._albums:
                # Start a new song if not playing
                if self._current_playback_track.id is None or\
                        isinstance(self._current_playback_track, Radio):
                    track = self.__get_tracks_random()
                    self.load(track)
                elif not self.is_playing:
                    self.play()
        else:
            # We want current album to continue playback
            self._albums = [self._current_playback_track.album]
        if self._current_playback_track.id is not None:
            self.set_next()
            self.set_prev()
        self.emit("party-changed", party)
        self.emit("playback-changed")

    def set_party_ids(self):
        """
            Set party mode ids
        """
        party_ids = App().settings.get_value("party-ids")
        album_ids = App().albums.get_ids([], party_ids, True)
        if not album_ids:
            album_ids = App().albums.get_ids([], party_ids, False)
        self._albums = []
        for album_id in album_ids:
            album = Album(album_id, [], [], True)
            self._albums.append(album)

    @property
    def is_party(self):
        """
            True if party mode on
            @return bool
        """
        return self.__is_party

    @property
    def shuffle_has_next(self):
        """
            True if history provide a next track
            @return bool
        """
        return self.__history and self.__history.has_next

    @property
    def shuffle_has_prev(self):
        """
            True if history provide a prev track
            @return bool
        """
        return self.__history and self.__history.has_prev

#######################
# PROTECTED           #
#######################
    def _on_stream_start(self, bus, message):
        """
            On stream start add to shuffle history
        """
        if self._current_playback_track.id is None or\
                self._current_playback_track.id < 0:
            return
        # Add track to shuffle history if needed
        if self._shuffle == Shuffle.TRACKS or self.__is_party:
            if self.__history:
                next = self.__history.next
                prev = self.__history.prev
                # Remove next track
                if next is not None and\
                        self._current_playback_track == next.value:
                    next = self.__history.next
                    next.set_prev(self.__history)
                    self.__history = next
                # Remove previous track
                elif prev is not None and\
                        self._current_playback_track == prev.value:
                    prev = self.__history.prev
                    prev.set_next(self.__history)
                    self.__history = prev
                # Add a new track
                elif self.__history.value != self._current_playback_track:
                    new_list = LinkedList(self._current_playback_track,
                                          None,
                                          self.__history)
                    self.__history = new_list
            else:
                # Initial history
                new_list = LinkedList(self._current_playback_track)
                self.__history = new_list
            self.__add_to_shuffle_history(self._current_playback_track)

#######################
# PRIVATE             #
#######################
    def __set_shuffle(self, settings, value):
        """
            Set shuffle mode to gettings value
            @param settings as Gio.Settings, value as str
        """
        self._shuffle = App().settings.get_enum("shuffle")

        if self._plugins1.rgvolume is not None and\
           self._plugins2.rgvolume is not None:
            if self._shuffle == Shuffle.TRACKS:
                self._plugins1.rgvolume.props.album_mode = 0
                self._plugins2.rgvolume.props.album_mode = 0
            else:
                self._plugins1.rgvolume.props.album_mode = 1
                self._plugins2.rgvolume.props.album_mode = 1
        if self._current_playback_track.id is not None:
            self.set_next()

    def __get_next(self):
        """
            Next track in shuffle mode
            @return track as Track
        """
        try:
            if self._shuffle == Shuffle.TRACKS or self.__is_party:
                if self._albums:
                    track = self.__get_tracks_random()
                    # All track dones
                    # Try to get another one track after reseting history
                    if track.id is None:
                        self.__already_played_albums = []
                        self.__already_played_tracks = {}
                        self.__history = []
                        repeat = App().settings.get_enum("repeat")
                        if repeat == Repeat.ALL:
                            return self.__get_next()
                    return track
        except Exception as e:  # Recursion error
            Logger.error("ShufflePLayer::__get_next(): %s", e)
        return Track()

    def __get_tracks_random(self):
        """
            Return a random track and make sure it has never been played
            @return Track
        """
        for album in sorted(self._albums, key=lambda *args: random.random()):
            for track in sorted(album.tracks,
                                key=lambda *args: random.random()):
                # Ignore current track, not an issue if playing one track
                # in shuffle because LinearPlayer will handle next()
                if track != App().player.current_track and (
                        album not in self.__already_played_tracks.keys() or
                        track not in self.__already_played_tracks[album]):
                    return track
            if album in self.__already_played_tracks.keys():
                self.__already_played_tracks.pop(album)
                self.__already_played_albums.append(album)
        return Track()

    def __add_to_shuffle_history(self, track):
        """
            Add a track to shuffle history
            @param track as Track
        """
        if track.album not in self.__already_played_tracks.keys():
            self.__already_played_tracks[track.album] = []
        if track not in self.__already_played_tracks[track.album]:
            self.__already_played_tracks[track.album].append(track)
