"""Line-mode frontend: plain ASCII, one line in, one reply out.

Built for 1200-baud AX.25 packet radio, where a full-screen redraw costs half a
minute of airtime. Imports only `tos.engine` (and PyYAML through it), never Textual.
"""
