# This is time (in seconds) to attempt to load a website to get its title
# before giving up. (default: 10)
TIMEOUT = 10

# This is the number of bytes to read before giving up on finding a title tag
# on the page. (default: 512KB (512 * 1024))
READ_BYTES = 512 * 1024

# This is the time (in seconds) between looking up the same title again. This
# is an anti-spam measure.
LOOKUP_COOLOFF = 18
