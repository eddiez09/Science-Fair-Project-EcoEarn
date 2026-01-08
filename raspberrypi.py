#!/usr/bin/env python3
"""Raspberry Pi sensor monitor.

Monitors a laser break-beam sensor (GPIO) and a 10kg load cell via HX711.
When the beam is broken AND the weight increases above a threshold, sends
an UDP message to a laptop to indicate an award (e.g. "AWARD 25").

Configure pins and network destination via command-line arguments.
"""
import argparse
import socket
import time
import sys

try:
	import RPi.GPIO as GPIO  # type: ignore
except Exception:
	GPIO = None

try:
	from hx711 import HX711  # type: ignore
except Exception:
	HX711 = None


def setup_gpio(beam_pin):
	if GPIO is None:
		raise RuntimeError('RPi.GPIO not available. Run on a Raspberry Pi.')
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(beam_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def read_weight(hx, samples=5):
	# Read multiple times and average to smooth noise
	vals = []
	for _ in range(samples):
		try:
			w = hx.get_weight(5)
		except Exception:
			# Try alternative method name used by some HX711 libs
			w = hx.read() if hasattr(hx, 'read') else 0
		vals.append(float(w))
		time.sleep(0.01)
	# Remove outliers and average
	vals.sort()
	if len(vals) > 2:
		vals = vals[1:-1]
	return sum(vals) / len(vals) if vals else 0.0


def main():
	parser = argparse.ArgumentParser(description='Pi monitor: beam + load cell -> award UDP')
	parser.add_argument('--beam-pin', type=int, default=17, help='GPIO BCM pin for break-beam input')
	parser.add_argument('--dout', type=int, default=5, help='HX711 DOUT pin (BCM)')
	parser.add_argument('--pd-sck', type=int, default=6, help='HX711 SCK pin (BCM)')
	parser.add_argument('--ref-unit', type=float, default=1.0, help='Reference unit / scale factor for load cell')
	parser.add_argument('--threshold-g', type=float, default=50.0, help='Minimum weight increase in grams to consider')
	parser.add_argument('--host', type=str, default=None, help='Laptop IP address to send award to (if omitted, broadcast will be used)')
	parser.add_argument('--port', type=int, default=5005, help='UDP port on laptop')
	parser.add_argument('--cooldown', type=float, default=3.0, help='Seconds to wait after sending an award')
	args = parser.parse_args()

	if GPIO is None:
		print('RPi.GPIO module not found. This script must run on a Raspberry Pi.', file=sys.stderr)
		sys.exit(1)
	if HX711 is None:
		print('hx711 library not found. Install via pip (e.g. hx711).', file=sys.stderr)
		sys.exit(1)

	setup_gpio(args.beam_pin)

	# Initialize HX711
	hx = HX711(dout_pin=args.dout, pd_sck_pin=args.pd_sck) if 'dout_pin' in HX711.__init__.__code__.co_varnames else HX711(args.dout, args.pd_sck)
	try:
		# Common methods used by hx711 libs
		if hasattr(hx, 'set_reading_format'):
			hx.set_reading_format('MSB', 'MSB')
		if hasattr(hx, 'set_reference_unit'):
			hx.set_reference_unit(args.ref_unit)
		if hasattr(hx, 'reset'):
			hx.reset()
		if hasattr(hx, 'tare'):
			hx.tare()
	except Exception:
		pass

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	dst = args.host if args.host else 'broadcast'
	print(f'Starting monitor: beam_pin={args.beam_pin} dout={args.dout} pd_sck={args.pd_sck} -> {dst}:{args.port}')

	# Baseline weight reading
	try:
		baseline = read_weight(hx, samples=10)
	except Exception:
		baseline = 0.0
	print(f'Baseline weight: {baseline:.2f}')

	last_sent = 0

	try:
		while True:
			# Read beam state (assume pulled HIGH when unobstructed with pull-up)
			beam_state = GPIO.input(args.beam_pin)
			beam_broken = (beam_state == GPIO.LOW)

			# Read current weight
			try:
				w = read_weight(hx, samples=5)
			except Exception:
				w = 0.0

			delta = w - baseline

			# Debug
			print(f'beam_broken={beam_broken} weight={w:.2f} delta={delta:.2f}', end='\r')

			now = time.time()
			if beam_broken and delta >= args.threshold_g and (now - last_sent) >= args.cooldown:
				msg = f'AWARD 25'
				try:
					if args.host:
						sock.sendto(msg.encode('utf-8'), (args.host, args.port))
					else:
						# Broadcast on common AP subnet
						sock.sendto(msg.encode('utf-8'), ('192.168.4.255', args.port))
					print()  # newline after debug carriage
					print(f'Sent award to {args.host}:{args.port}: {msg}')
				except Exception as e:
					print(f'Failed to send UDP message: {e}', file=sys.stderr)
				last_sent = now

			time.sleep(0.05)

	except KeyboardInterrupt:
		print('\nExiting...')
	finally:
		try:
			GPIO.cleanup()
		except Exception:
			pass


if __name__ == '__main__':
	main()

