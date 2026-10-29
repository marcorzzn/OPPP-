"""Genera le icone PWA, il logo UI e la favicon a partire dal logo ufficiale del progetto.

Sorgente: public/assets/aistudio/image_c00a7e25.png (RGBA 8-bit).
Zero dipendenze esterne: usa solo `zlib` e `struct` della libreria standard Python.
"""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_LOGO = os.path.join(ROOT, "public", "assets", "aistudio", "image_c00a7e25.png")
OUT_DIR = os.path.join(ROOT, "icons")
os.makedirs(OUT_DIR, exist_ok=True)


def decode_png_rgba(path: str):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG"
    pos = 8
    w = h = 0
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        if ctype == b"IHDR":
            w, h, bd, ct, comp, filt, inter = struct.unpack(">IIBBBBB", chunk)
            assert bd == 8 and ct == 6 and inter == 0, f"Unsupported PNG format: bd={bd} ct={ct}"
        elif ctype == b"IDAT":
            idat.extend(chunk)
        elif ctype == b"IEND":
            break
        pos += 12 + length

    raw = zlib.decompress(bytes(idat))
    stride = w * 4
    pixels = bytearray(w * h * 4)

    def paeth(a, b, c):
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    in_pos = 0
    for y in range(h):
        ftype = raw[in_pos]
        in_pos += 1
        row_out = y * stride
        prev_out = (y - 1) * stride
        for x in range(stride):
            val = raw[in_pos]
            in_pos += 1
            a = pixels[row_out + x - 4] if x >= 4 else 0
            b = pixels[prev_out + x] if y > 0 else 0
            c = pixels[prev_out + x - 4] if (y > 0 and x >= 4) else 0
            if ftype == 0:
                recon = val
            elif ftype == 1:
                recon = (val + a) & 0xFF
            elif ftype == 2:
                recon = (val + b) & 0xFF
            elif ftype == 3:
                recon = (val + ((a + b) >> 1)) & 0xFF
            elif ftype == 4:
                recon = (val + paeth(a, b, c)) & 0xFF
            else:
                raise ValueError(f"Unknown PNG filter {ftype}")
            pixels[row_out + x] = recon
    return w, h, pixels


def remove_white_bg_and_crop(w: int, h: int, pixels: bytearray):
    """Flood-fills outer white/near-white background to transparent with smooth edge anti-aliasing and crops to tight bounding box."""
    visited = bytearray(w * h)
    bg_mask = bytearray(w * h)
    queue = []

    def is_bg_candidate(idx):
        p = idx * 4
        r, g, b, a = pixels[p], pixels[p + 1], pixels[p + 2], pixels[p + 3]
        if a < 16:
            return True
        # Near-white neutral pixel
        return r >= 236 and g >= 236 and b >= 236 and max(r, g, b) - min(r, g, b) <= 18

    for x in range(w):
        for y in (0, h - 1):
            i = y * w + x
            if not visited[i] and is_bg_candidate(i):
                visited[i] = 1
                queue.append(i)
    for y in range(h):
        for x in (0, w - 1):
            i = y * w + x
            if not visited[i] and is_bg_candidate(i):
                visited[i] = 1
                queue.append(i)

    head = 0
    while head < len(queue):
        curr = queue[head]
        head += 1
        bg_mask[curr] = 1
        cx = curr % w
        cy = curr // w
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                ni = ny * w + nx
                if not visited[ni] and is_bg_candidate(ni):
                    visited[ni] = 1
                    queue.append(ni)

    out = bytearray(pixels)
    for i in range(w * h):
        p = i * 4
        if bg_mask[i]:
            out[p] = 0
            out[p + 1] = 0
            out[p + 2] = 0
            out[p + 3] = 0
        else:
            # Check if within 2px of background to unmatte white anti-aliasing halo
            cx = i % w
            cy = i // w
            near_bg = False
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and bg_mask[ny * w + nx]:
                        near_bg = True
                        break
                if near_bg:
                    break
            if near_bg:
                r, g, b, a = out[p], out[p + 1], out[p + 2], out[p + 3]
                if max(r, g, b) - min(r, g, b) < 36:
                    # Neutral charcoal border blended with white (255,255,255)
                    lum = (r + g + b) / 3.0
                    if lum > 42:
                        alpha = max(0.0, min(1.0, (250.0 - lum) / (250.0 - 32.0)))
                        out[p] = 24
                        out[p + 1] = 25
                        out[p + 2] = 28
                        out[p + 3] = int(round(a * alpha))
                else:
                    # Colored (orange) edge blended with white: estimate alpha from blue channel
                    if b > 25:
                        alpha = max(0.05, min(1.0, (250.0 - b) / 235.0))
                        ur = int(min(255, max(0, round((r - (1.0 - alpha) * 255.0) / alpha))))
                        ug = int(min(255, max(0, round((g - (1.0 - alpha) * 255.0) / alpha))))
                        ub = int(min(255, max(0, round((b - (1.0 - alpha) * 255.0) / alpha))))
                        out[p] = ur
                        out[p + 1] = ug
                        out[p + 2] = ub
                        out[p + 3] = int(round(a * alpha))

    # Find bounding box of non-transparent pixels
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if out[(y * w + x) * 4 + 3] > 10:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    cw = max_x - min_x + 1
    ch = max_y - min_y + 1
    cropped = bytearray(cw * ch * 4)
    for y in range(ch):
        src_off = ((min_y + y) * w + min_x) * 4
        dst_off = y * cw * 4
        cropped[dst_off : dst_off + cw * 4] = out[src_off : src_off + cw * 4]
    return cw, ch, cropped


def render_square_icon(src_w: int, src_h: int, src_px: bytearray, size: int, pad_ratio: float = 0.06, bg_rgba=None) -> bytes:
    """Resamples cropped logo onto a `size x size` square canvas using area/bilinear sampling."""
    canvas = bytearray(size * size * 4)
    if bg_rgba is not None:
        br, bg, bb, ba = bg_rgba
        for i in range(0, size * size * 4, 4):
            canvas[i] = br
            canvas[i + 1] = bg
            canvas[i + 2] = bb
            canvas[i + 3] = ba

    avail = size * (1.0 - 2.0 * pad_ratio)
    scale = min(avail / src_w, avail / src_h)
    dst_w = max(1, int(round(src_w * scale)))
    dst_h = max(1, int(round(src_h * scale)))
    off_x = (size - dst_w) // 2
    off_y = (size - dst_h) // 2

    # Box/area + bilinear hybrid downsampling for crisp icons at all sizes
    inv_scale_x = src_w / float(dst_w)
    inv_scale_y = src_h / float(dst_h)

    for dy in range(dst_h):
        sy0 = dy * inv_scale_y
        sy1 = (dy + 1) * inv_scale_y
        iy0 = max(0, int(math.floor(sy0)))
        iy1 = min(src_h - 1, int(math.ceil(sy1)) - 1)
        for dx in range(dst_w):
            sx0 = dx * inv_scale_x
            sx1 = (dx + 1) * inv_scale_x
            ix0 = max(0, int(math.floor(sx0)))
            ix1 = min(src_w - 1, int(math.ceil(sx1)) - 1)

            if ix1 > ix0 or iy1 > iy0:
                # Area average with premultiplied alpha
                r_acc = g_acc = b_acc = a_acc = w_acc = 0.0
                for sy in range(iy0, iy1 + 1):
                    wy = min(sy + 1.0, sy1) - max(float(sy), sy0)
                    if wy <= 0:
                        continue
                    for sx in range(ix0, ix1 + 1):
                        wx = min(sx + 1.0, sx1) - max(float(sx), sx0)
                        if wx <= 0:
                            continue
                        wgt = wx * wy
                        p = (sy * src_w + sx) * 4
                        sa = src_px[p + 3] / 255.0
                        r_acc += src_px[p] * sa * wgt
                        g_acc += src_px[p + 1] * sa * wgt
                        b_acc += src_px[p + 2] * sa * wgt
                        a_acc += sa * wgt
                        w_acc += wgt
                if w_acc > 0 and a_acc > 1e-5:
                    out_a = a_acc / w_acc
                    sr = int(min(255, max(0, round(r_acc / a_acc))))
                    sg = int(min(255, max(0, round(g_acc / a_acc))))
                    sb = int(min(255, max(0, round(b_acc / a_acc))))
                    sa_int = int(min(255, max(0, round(out_a * 255.0))))
                else:
                    sr = sg = sb = sa_int = 0
            else:
                p = (iy0 * src_w + ix0) * 4
                sr, sg, sb, sa_int = src_px[p], src_px[p + 1], src_px[p + 2], src_px[p + 3]

            if sa_int == 0:
                continue

            dp = ((off_y + dy) * size + (off_x + dx)) * 4
            if bg_rgba is None or canvas[dp + 3] == 0:
                canvas[dp] = sr
                canvas[dp + 1] = sg
                canvas[dp + 2] = sb
                canvas[dp + 3] = sa_int
            else:
                # Alpha composite over background
                fa = sa_int / 255.0
                inv = 1.0 - fa
                canvas[dp] = int(round(sr * fa + canvas[dp] * inv))
                canvas[dp + 1] = int(round(sg * fa + canvas[dp + 1] * inv))
                canvas[dp + 2] = int(round(sb * fa + canvas[dp + 2] * inv))
                canvas[dp + 3] = 255

    return bytes(canvas)


def encode_png(size: int, rgba_bytes: bytes) -> bytes:
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)
        raw.extend(rgba_bytes[y * stride : (y + 1) * stride])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def encode_ico(png_entries: list[tuple[int, bytes]]) -> bytes:
    """Builds a standard Windows/Web .ico container embedding PNG payloads (16, 32, 48)."""
    count = len(png_entries)
    header = struct.pack("<HHH", 0, 1, count)
    dirs = bytearray()
    payloads = bytearray()
    offset = 6 + count * 16
    for size, png_data in png_entries:
        w_byte = 0 if size >= 256 else size
        h_byte = 0 if size >= 256 else size
        dirs.extend(
            struct.pack(
                "<BBBBHHII",
                w_byte,
                h_byte,
                0,
                0,
                1,
                32,
                len(png_data),
                offset,
            )
        )
        payloads.extend(png_data)
        offset += len(png_data)
    return header + bytes(dirs) + bytes(payloads)


def main():
    w, h, px = decode_png_rgba(SRC_LOGO)
    cw, ch, cropped = remove_white_bg_and_crop(w, h, px)
    print(f"Loaded source logo {w}x{h} -> cropped transparent logo {cw}x{ch}")

    targets = [
        (os.path.join(OUT_DIR, "logo.png"), 256, 0.04, None),
        (os.path.join(OUT_DIR, "icon-192.png"), 192, 0.05, None),
        (os.path.join(OUT_DIR, "icon-512.png"), 512, 0.05, None),
        (os.path.join(OUT_DIR, "icon-maskable.png"), 512, 0.16, (18, 19, 22, 255)),
        (os.path.join(OUT_DIR, "apple-touch-icon.png"), 180, 0.08, (18, 19, 22, 255)),
        (os.path.join(OUT_DIR, "favicon-32.png"), 32, 0.03, None),
    ]

    for path, size, pad, bg in targets:
        rgba = render_square_icon(cw, ch, cropped, size, pad_ratio=pad, bg_rgba=bg)
        data = encode_png(size, rgba)
        with open(path, "wb") as f:
            f.write(data)
        print(f"wrote {os.path.relpath(path, ROOT)} ({len(data)} B)")

    ico_entries = []
    for sz in (16, 32, 48):
        rgba = render_square_icon(cw, ch, cropped, sz, pad_ratio=0.02, bg_rgba=None)
        ico_entries.append((sz, encode_png(sz, rgba)))

    ico_bytes = encode_ico(ico_entries)
    ico_path = os.path.join(ROOT, "favicon.ico")
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)
    print(f"wrote favicon.ico ({len(ico_bytes)} B)")


if __name__ == "__main__":
    main()
