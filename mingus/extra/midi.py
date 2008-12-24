"""

================================================================================

	mingus - Music theory Python package, MIDI sequencer
	Copyright (C) 2008, Bart Spaans

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

================================================================================

   This module provides a MidiSequencer which will take the objects from 
   mingus.containers and turn them into MIDI messages.

================================================================================

"""

from datetime import datetime
from mingus.containers.Instrument import MidiInstrument

class MidiSequencer:
	"""Simple MidiSequencer; supports `note on`, `note off` and `select`"""

	output = None


	def __init__(self, output_function = None):
		"""The output_function can be set to redirect the generated messages. \
For an example see the source mingus.extra.fluidsynth.py"""

		self.output = output_function


	def write(self, msg):
		"""Writes a message to the output function."""
		if self.output == None:
			print msg
			return True
		try:
			self.output(msg)
			return True
		except:
			return False


	def set_instrument(self, channel, instr):
		"""Sets the channel to the instrument _instr_."""
		return self.write("select %d 1 0 %d\n" % (channel, instr))


	def play_Note(self, note, channel = 1, velocity = 100):
		"""Plays a Note object on a channel[1-16] with a velocity[0-127]."""
		return self.write("noteon %d %d %d\n" % (channel, int(note) + 12, velocity))

	def control_change(self, channel, control, value):
		return self.write("cc %d %d %d\n" % (channel, control, value)



	def stop_everything(self):
		"""Stops all the notes on all channels."""
		for x in range(118):
			for c in range(16):
				self.stop_Note(x, c)

	def stop_Note(self, note, channel = 1):
		"""Stops a note on a channel."""
		return self.write("noteoff %d %d\n" % (channel, int(note) + 12))




	def play_NoteContainer(self, nc, channel = 1, velocity = 100):
		"""Plays the Notes in the NoteContainer nc."""
		for note in nc:
			if not self.play_Note(note, channel, velocity):
				return False
		return True



	def stop_NoteContainer(self, nc, channel = 1):
		"""Stops playing the notes in NoteContainer nc."""
		for note in nc:
			if not self.stop_Note(note, channel):
				return False
		return True



	def play_Bar(self, bar, channel = 1, duration = 2000):
		"""Plays a Bar object. The duration is the duration of the \
whole bar in milliseconds. The default is set to 2000 ms which is good for \
120 bpm when playing bars in 4/4."""
		for nc in bar:
			n = datetime.now()

			if not self.play_NoteContainer(nc[2], channel, 100):
				return False
			a = datetime.now()
			
			while (a - n).microseconds / 1000.0 < (duration * (1.0 / nc[1])):
				a = datetime.now()

			self.stop_NoteContainer(nc[2], channel)

		return True


	def play_Bars(self, bars, channels, duration = 2000):
		"""Plays several bars (a list of Bar objects) at the same time. A list of \
channels should also be provided."""


		tick = 0.0  # place in beat from 0.0 to bar.length
		cur = []    # keeps the index of the note needing investigation in each of bars
		playing = [] # keeps track of the notecontainers being played right now.


		# Prepare cur list
		for x in bars:
			cur.append(0)

		n = datetime.now()
		
		while tick < bars[0].length:

			# Check each bar in bars and investigate index in cur.
			for x in range(len(bars)):

				bar = bars[x]
				current_nc = bar[cur[x]]

				# Should note be played?
				if current_nc[0] <= tick and \
					current_nc[0] + \
					(1.0 / current_nc[1]) >= tick \
					and [current_nc[0], current_nc[1], current_nc[2],\
						channels[x]] not in playing:

					self.play_NoteContainer(current_nc[2], channels[x])
					playing.append([current_nc[0], current_nc[1],\
							current_nc[2], channels[x]])
					if cur[x] != len(bar) - 1:
						cur[x] += 1

			# Should any notes stop playing?
			for p in playing:
				if p[0] + (1.0 / p[1]) <= tick:
					self.stop_NoteContainer(p[2], p[3])
					playing.remove(p)

			

			# Milliseconds so far
			a = datetime.now()
			millis = (a - n).microseconds / 1000.0 + (a - n).seconds * 1000.0

			# Calculate new tick
			tick = (millis / duration) * bars[0].length
			
		# Stop all the notes that are still playing
		for p in playing:
			self.stop_NoteContainer(p[2], p[3])
			playing.remove(p)

		return True


	def play_Track(self, track, channel = 1):
		"""Plays a Track object."""
		for bar in track:
			# bpm attribute needed? Or just another argument?
			if not self.play_Bar(bar, channel, 2000):
				return False
		return True

	def play_Tracks(self, tracks, channels, keep_playing_func = True):
		"""Plays a list of Tracks. keep_playing_func can be used to pass a function, \
which will determine if the tracks should keep playing after each played bar."""
		
		# Set the right instruments
		for x in range(len(tracks)):
			instr = tracks[x].instrument
			if isinstance(instr, MidiInstrument):
				try: 
					i = instr.names.index(instr.name)
				except:
					i = 1
				self.set_instrument(channels[x], i)
			else:
				self.set_instrument(channels[x], 1)

		
		current_bar = 0
		max_bar = len(tracks[0])

		# Play the bars
		while keep_playing_func and current_bar < max_bar:
			playbars = []
			for tr in tracks:
				playbars.append(tr[current_bar])
			if not self.play_Bars(playbars, channels):
				return False
			current_bar += 1

		return True
			

	def play_Composition(self, composition, channels = None, keep_playing_func = True):
		"""Plays a Composition object."""

		if channels == None:
			channels = map(lambda x: x + 1, range(len(composition.tracks)))
		return self.play_Tracks(composition.tracks, channels, keep_playing_func)
