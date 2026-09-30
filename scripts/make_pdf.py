#!/usr/bin/env python3
"""Minimal dependency-free PDF writer (text-only, Helvetica).

Produces a valid single- or multi-page PDF with selectable/extractable text
so Databricks ai_parse_document / ai_extract can read it. Not fancy, but real.

API:
  from make_pdf import write_pdf
  write_pdf("out.pdf", title="...", lines=[("H1","Heading"),("P","body"), ...])
Line kinds: H1 (18pt bold-ish), H2 (13pt), P (11pt), SP (blank spacer).
"""

def _esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(text, width_chars):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def write_pdf(path, title, lines):
    # Build content stream(s), paginating at ~52 lines/page.
    page_streams = []
    y = 760
    left = 60
    parts = []

    def flush():
        nonlocal parts
        if parts:
            page_streams.append("\n".join(parts))
            parts = []

    def emit(text, size, dy_before):
        nonlocal y
        if y < 70:
            flush()
            y = 760
        y -= dy_before
        parts.append(f"BT /F1 {size} Tf {left} {y} Td ({_esc(text)}) Tj ET")

    # Title
    emit(title, 20, 10)
    y -= 6
    for kind, text in lines:
        if kind == "SP":
            y -= 10
            continue
        size = {"H1": 16, "H2": 13, "P": 11}.get(kind, 11)
        width = {"H1": 60, "H2": 70, "P": 90}.get(kind, 90)
        first = True
        for wl in _wrap(text, width):
            emit(wl, size, (14 if kind == "P" else 20) if first else 14)
            first = False
    flush()
    if not page_streams:
        page_streams = [""]

    # Assemble PDF objects.
    objs = []
    font_obj_num = None  # assigned later
    n_pages = len(page_streams)
    # Object numbering: 1=Catalog, 2=Pages, then per page: Page + Content, then Font last.
    page_obj_nums = []
    content_obj_nums = []
    num = 3
    for _ in range(n_pages):
        page_obj_nums.append(num); num += 1
        content_obj_nums.append(num); num += 1
    font_obj_num = num

    objs.append((1, "<< /Type /Catalog /Pages 2 0 R >>"))
    kids = " ".join(f"{p} 0 R" for p in page_obj_nums)
    objs.append((2, f"<< /Type /Pages /Count {n_pages} /Kids [{kids}] >>"))
    for i, stream in enumerate(page_streams):
        pnum = page_obj_nums[i]; cnum = content_obj_nums[i]
        objs.append((pnum,
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> /Contents {cnum} 0 R >>"))
        data = stream.encode("latin-1", "replace")
        objs.append((cnum,
            f"<< /Length {len(data)} >>\nstream\n{stream}\nendstream", True))
    objs.append((font_obj_num,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"))

    objs.sort(key=lambda o: o[0])
    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = {}
    for obj in objs:
        onum, body = obj[0], obj[1]
        offsets[onum] = len(out)
        out += f"{onum} 0 obj\n".encode("latin-1")
        out += body.encode("latin-1", "replace")
        out += b"\nendobj\n"
    xref_pos = len(out)
    max_obj = max(offsets)
    out += f"xref\n0 {max_obj+1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for i in range(1, max_obj + 1):
        out += f"{offsets.get(i,0):010d} 00000 n \n".encode("latin-1")
    out += f"trailer\n<< /Size {max_obj+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("latin-1")
    with open(path, "wb") as f:
        f.write(out)
    return path


if __name__ == "__main__":
    write_pdf("/tmp/_test.pdf", "Test Document",
              [("H2", "Section"), ("P", "Hello world " * 20)])
    print("wrote /tmp/_test.pdf")
