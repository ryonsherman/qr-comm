#!/usr/bin/env python2

import os
import time
import qrcode
import shutil
import logging
import tempfile
import argparse

# get python log
log = logging.getLogger()
# set default log level
log.setLevel(logging.DEBUG)
# define log format
log_format = "[%(asctime)s] (%(levelname)s) %(message)s"

# initialize argument parser
parser = argparse.ArgumentParser()
# initialize 'mode' subparsers
subparsers = parser.add_subparsers(dest='mode',
    help='operation mode')

# initialize 'rx' mode subparser
subparser = subparsers.add_parser('rx',
    help="receive mode")

subparser.add_argument('source', 
    help="source device, image, or directory of images")

# initialize 'tx' mode subparser
subparser = subparsers.add_parser('tx',
    help="transmit mode")

# define 'payload' argument type
def payload(path):
    if os.path.exists(path): return path
    parser.error("The file '%s' does not exist!" % path)
# add required binary 'payload' argument
subparser.add_argument('payload', type=payload,
    help="binary payload")
# create 'payload' optional argument group
group = subparser.add_argument_group('payload')
# add optional 'bytes' size argument
group.add_argument('--bytes', type=int, default=1024,
    help="bytes per frame (default: %(default)s)")
# add optional 'zlib' compression argument
group.add_argument('--zlib', action='store_true',
    help="use zlib compression")

# create 'qrcode' optional argument group
group = subparser.add_argument_group('qr code')
# add optional qr code 'size' argument
group.add_argument('--size', type=int, default=450,
    help="qr code image size (default: %(default)s)")
# add optional qr code frame 'delay'
group.add_argument('--delay', type=float, default=1,
    help="delay between qr code images (default: %(default)s)")
# add optional qr code 'version' argument
group.add_argument('--ver', type=int, default=25,
    help="qr code version (default: %(default)s)")
# determine 'ec' argument choices
choices = [x[-1] for x in 
    filter(lambda x: x.startswith('ERROR_CORRECT_'), 
        qrcode.constants.__dict__.keys())]
# add optional qr code 'error correction' argument
group.add_argument('--ec',
    type=lambda x: x.upper(), choices=choices, default='L',
    help="qr code error correction level (default: %(default)s)")

# add optional 'display' argument
subparser.add_argument('--display', action='store_true',
    help="display qr code images after generation (default if no outfile)")
# add optional 'silent' console output argument
parser.add_argument('--silent', action='store_true',
    help="silence console output")
# add 'outfile' argument type
def outfile(path):
    # determine outfile directory path
    _path = os.path.dirname(os.path.abspath(path))
    # return path if writable
    if os.access(_path, os.W_OK):
        return path
    subparser.error("The directory '%s' is not writable!" % _path)
# add optional 'outfile' argument
subparser.add_argument('outfile',
    type=outfile, nargs='?',
    help="output animated gif image")

# parse arguments
args = parser.parse_args()

# initialize console log handler
if not args.silent:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(log_format))
    log.addHandler(handler)

# operate in 'receive' mode
if args.mode == 'rx':
    pass
# end of 'receive' mode
# operate in 'transmit' mode
elif args.mode == 'tx':
    # determine image size
    args.size = (args.size, args.size)
    # determine error correction level
    args.ec = getattr(qrcode.constants, 
        'ERROR_CORRECT_%s' % args.ec.upper())
    # create qr encoder
    qr = qrcode.QRCode(
        version=args.ver, 
        error_correction=args.ec)

    # read payload binary
    with open(args.payload, 'rb') as f:
        payload = f.read()

    # compress payload if requested
    if args.zlib:
        import zlib
        before = len(payload)
        _payload = zlib.compress(payload, 
            zlib.Z_BEST_COMPRESSION)
        after = len(_payload)
        size = after - before
        ratio = 100 * after/before
        log.info("Compressing %s -> %s bytes [%s%%]" % (before, after, ratio))
        if after >= before:
            log.warning("Compressed file larger than source; decompressing...")
        else: payload = _payload

    # initialize temp directory
    temp = tempfile.mkdtemp()
    # initialize total size
    size, total = 0, len(payload)
    # determine segment count
    count = (total / args.bytes) + 1
    # determine total duration
    duration = args.delay * count
    # initialize elapsed time
    elapsed = 0

    # log encoding start
    log.info("Encoding payload of %s bytes; %s frames (%s seconds)" % (
        total, count, duration))

    # determine start time
    start = time.time()
    # initialize run times
    timed = []
    # iterate payload by X 'bytes' per segment
    for i in range(0, total, args.bytes):
        # determine run start time
        run = time.time()
        # determine segment number
        num = int((i / args.bytes) + 1)
        # read payload segment
        segment = payload[i:i + args.bytes]
        # increment total size
        size += len(segment)
        # determine completion percentage
        ratio = 100 * size / total

        # log frame generation
        log.info("Generating frame %s of %s; " \
            "%s/%s (%s bytes) [%s%%]" % (
                num, count, size, total - size, len(segment), ratio))

        # qr encode segment
        qr.add_data(segment)
        qr.make()

        # create qr image
        img = qr.make_image()
        # resize image to requested size
        img.thumbnail(args.size)
        # save file to temp directory
        img.save(os.path.join(temp, str(i)))

        # clear qr image
        qr.clear()

        # determine run end time
        timed.append(time.time() - run)
        # determine average run time
        avg = sum(timed) / len(timed)
        # determine estimated remaining time
        remain = (count - num) * avg
        # determine estimated completion time
        now = time.localtime()
        complete = time.localtime(time.time() + remain)
        _format = ''
        if complete.tm_mday > now.tm_mday or complete.tm_mon > now.tm_mon:
            _format = '%m-%d '
        if complete.tm_year > now.tm_year:
            _format = '%Y-%m-%d '
        _format = _format + '%H:%M:%S'
        complete = time.strftime(_format, complete)

        # determine elapsed time
        elapsed += time.time() - start
        log.info("Run: %.2f, Avg: %.2f, Elapsed: %.2f, Remain: %.2f [%s]" % (
            timed[-1], avg, elapsed, remain, complete))

    # output file if requested
    if args.outfile:
        # log image conversion
        log.info("Saving file to '%s'" % args.outfile)
        # process image files
        import subprocess
        subprocess.call(
            'convert -delay %s -loop 0 %s %s' % (args.delay * 100,
            os.path.join(temp, '*'), args.outfile), shell=True)
    # display image if not saved or if requested
    if not args.outfile or args.display:
        import pygame
        # initialize screen
        screen = pygame.display.set_mode(args.size)
        # iterate image frames
        for i in range(0, total, args.bytes):
            # determine segment number
            num = str((i / args.bytes) + 1)
            # log frame display
            log.info("Displaying frame %s of %s for %ss" % (
                num, count, args.delay))
            # load image from temp directory
            img = pygame.image.load(os.path.join(temp, str(i)))
            # output image to screen
            screen.blit(img, (0, 0))
            # flip screen to display
            pygame.display.flip()
            # add time delay
            time.sleep(args.delay)

    # remove temp directory
    shutil.rmtree(temp)
# end of 'transmit' mode
