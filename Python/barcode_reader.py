#!/usr/bin/env python3
import cv2
from pyzbar import pyzbar
import argparse
import time

# QR code to username mapping
QR_USERS = {
    '1234': 'Ryan',
}

# Barcode to product name mapping
BARCODES = {
    '0838766101903': 'VEGA Plant-based Protein Shake',
    '0017082873590': 'Jack Links Turkey Jerky (NON-RECYCLABLE)',
}

def decode_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    results = []
    for b in barcodes:
        data = b.data.decode('utf-8', errors='replace')
        barcode_type = b.type
        (x, y, w, h) = b.rect
        results.append({'data': data, 'type': barcode_type, 'rect': (x, y, w, h)})
    #!/usr/bin/env python3
    import cv2
    from pyzbar import pyzbar
    import argparse
    import time
    import threading
    import socket

    # QR code to username mapping
    QR_USERS = {
        '1234': 'Ryan',
    }

    # Barcode to product name mapping
    BARCODES = {
        '0838766101903': 'VEGA Plant-based Protein Shake',
        '0017082873590': 'Jack Links Turkey Jerky (NON-RECYCLABLE)',
    }


    def decode_barcodes(frame):
        barcodes = pyzbar.decode(frame)
        results = []
        for b in barcodes:
            data = b.data.decode('utf-8', errors='replace')
            barcode_type = b.type
            (x, y, w, h) = b.rect
            results.append({'data': data, 'type': barcode_type, 'rect': (x, y, w, h)})
        return results


    def decode_qr_codes(frame):
        """Detect and decode QR codes using pyzbar (also supports QR codes)"""
        qr_codes = pyzbar.decode(frame)
        results = []
        for qr in qr_codes:
            if qr.type == 'QRCODE':
                data = qr.data.decode('utf-8', errors='replace')
                (x, y, w, h) = qr.rect
                results.append({'data': data, 'type': 'QRCODE', 'rect': (x, y, w, h)})
        return results


    def normalize_barcode(data: str) -> str:
        if data is None:
            return ''
        return data.strip()


    def find_barcode_name(raw: str) -> str:
        if raw is None:
            return 'Unknown Item'
        norm = normalize_barcode(raw)
        if norm in BARCODES:
            return BARCODES[norm]
        digits = ''.join(ch for ch in norm if ch.isdigit())
        if not digits:
            return 'Unknown Item'
        for k, v in BARCODES.items():
            k_digits = ''.join(ch for ch in str(k) if ch.isdigit())
            if k_digits == digits:
                return v
        return 'Unknown Item'


    def udp_listener(port, award_callback, stop_event):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(1.0)
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue
            try:
                msg = data.decode('utf-8').strip()
            except Exception:
                continue
            if msg.startswith('AWARD'):
                parts = msg.split()
                score = parts[1] if len(parts) > 1 else '25'
                award_callback(f'{score} points awarded')


    def main():
        parser = argparse.ArgumentParser(description='Camera barcode reader')
        parser.add_argument('--camera', type=int, default=0, help='Camera device index')
        parser.add_argument('--save', type=str, default=None, help='Optional file to log detected barcodes')
        parser.add_argument('--udp-port', type=int, default=5005, help='UDP port to listen for awards')
        args = parser.parse_args()

        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            print(f'Cannot open camera {args.camera}')
            return

        logfile = None
        if args.save:
            logfile = open(args.save, 'a', encoding='utf-8')

        # State management
        state = 'waiting_qr'  # waiting_qr, waiting_barcode
        current_user = None
        scanned_item = None
        scanned_item_time = 0
        last_scanned_barcode = None

        # Award overlay state
        award_message = None
        award_time = 0
        award_lock = threading.Lock()

        def set_award(msg: str):
            nonlocal award_message, award_time
            with award_lock:
                award_message = msg
                award_time = time.time()
            print(msg)

        stop_event = threading.Event()
        t = threading.Thread(target=udp_listener, args=(args.udp_port, set_award, stop_event), daemon=True)
        t.start()

        print('Press q to quit.')
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Decode both barcodes and QR codes
                barcodes = decode_barcodes(frame)
                qr_codes = decode_qr_codes(frame)
                all_detections = barcodes + qr_codes

                for b in all_detections:
                    x, y, w, h = b['rect']
                    color = (255, 0, 0) if b['type'] == 'QRCODE' else (0, 255, 0)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                    # Handle QR code for user login
                    if b['type'] == 'QRCODE' and state == 'waiting_qr':
                        if b['data'] in QR_USERS:
                            current_user = QR_USERS[b['data']]
                            state = 'waiting_barcode'
                            ts = time.strftime('%Y-%m-%d %H:%M:%S')
                            print(f'[{ts}] User logged in: {current_user}')
                            if logfile:
                                logfile.write(f'[{ts}] User logged in: {current_user}\n')
                                logfile.flush()

                    # Handle barcode for item scanning
                    elif b['type'] != 'QRCODE' and state == 'waiting_barcode':
                        scanned_norm = normalize_barcode(b['data'])
                        scanned_digits = ''.join(ch for ch in scanned_norm if ch.isdigit())
                        if scanned_digits != last_scanned_barcode:
                            last_scanned_barcode = scanned_digits
                            scanned_item_time = time.time()
                            item_name = find_barcode_name(b['data'])
                            scanned_item = item_name
                            ts = time.strftime('%Y-%m-%d %H:%M:%S')
                            print(f'[{ts}] {current_user} scanned: {item_name} raw={repr(b["data"])} digits={scanned_digits}')
                            if logfile:
                                logfile.write(f'[{ts}] {current_user} scanned: {item_name} raw={repr(b["data"])} digits={scanned_digits}\n')
                                logfile.flush()

                    text = f"{b['type']}: {b['data']}"
                    cv2.putText(frame, text, (x, y - 10 if y - 10 > 10 else y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # Draw state information on frame
                frame_height = frame.shape[0]
                frame_width = frame.shape[1]

                if state == 'waiting_qr':
                    cv2.putText(frame, 'Scan QR Code', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

                elif state == 'waiting_barcode':
                    cv2.putText(frame, '✓ Scan QR Code', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
                    cv2.putText(frame, f'Hello, {current_user}!', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

                    if scanned_item:
                        elapsed = time.time() - scanned_item_time
                        if elapsed < 2:
                            color_intensity = int(255 * (1 - elapsed / 2))
                            cv2.putText(frame, f'✓ {scanned_item}', (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, color_intensity, 0), 2)
                        else:
                            scanned_item = None
                    else:
                        cv2.putText(frame, 'Scan Barcode of item', (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)

                # Draw award overlay if present
                with award_lock:
                    if award_message and (time.time() - award_time) < 3:
                        txt = award_message
                        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)
                        x = (frame_width - tw) // 2
                        y = frame_height // 2
                        cv2.putText(frame, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 255), 3)

                cv2.imshow('Barcode & QR Code Reader', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break

        finally:
            stop_event.set()
            cap.release()
            cv2.destroyAllWindows()
            if logfile:
                logfile.close()


    if __name__ == '__main__':
        main()
