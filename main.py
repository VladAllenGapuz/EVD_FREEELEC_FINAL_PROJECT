"""BeadsLET: event-driven logic with PyScript."""
import asyncio, html, json, random, math
from pyscript import document, window, when

BEAD_PRICE = {"Acrylic": 0, "Mixed": 5, "Pearl-like": 10, "Gemstone-style": 15}
BASE, LETTER, CHARM = 50, 3, 10
KEY = "beadslet_cart"
MIX = ["#f1d98a", "#7d9bd8", "#8fb8a8", "#efe9f7"]

CATALOG = [
    {"id": 1, "image": "assets/products/product-1.svg", "title": "Classic Pearl", "tag": "minimalist", "unit": 65, "colors": ["#efe9f7", "#d9cfee"], "desc": "Pearl-like beads, clean and simple."},
    {"id": 2, "image": "assets/products/product-2.svg", "title": "Midnight Line", "tag": "minimalist", "unit": 55, "colors": ["#3a3350", "#8c84a8"], "desc": "Dark acrylic beads for everyday wear."},
    {"id": 3, "image": "assets/products/product-3.svg", "title": "Together Set", "tag": "couple", "unit": 120, "colors": ["#d98ba6", "#7d9bd8"], "desc": "Two matching bracelets for a pair."},
    {"id": 4, "image": "assets/products/product-4.svg", "title": "Bestie Trio", "tag": "friendship", "unit": 165, "colors": ["#8fb8a8", "#f1d98a"], "desc": "Three matching bracelets for friends."},
    {"id": 5, "image": "assets/products/product-5.svg", "title": "Little Star", "tag": "charm", "unit": 75, "colors": ["#b79bf0", "#f1d98a"], "desc": "Lilac beads with a star charm."},
    {"id": 6, "image": "assets/products/product-6.svg", "title": "Rose Heart", "tag": "charm", "unit": 75, "colors": ["#d98ba6", "#efe9f7"], "desc": "Rose beads with a heart charm."},
]
CHARMS = [("♥", "Heart"), ("★", "Star"), ("☾", "Moon")]
MAX_EACH = 3
state = {"color": "#d98ba6", "cart": [], "tag": "all", "charms": {s: [] for s, _ in CHARMS}}


def el(i): return document.getElementById(i)
def peso(n): return f"₱{n:,.0f}"
def esc(s): return html.escape(str(s))


def data(node, key):
    """Safely read a data-* attribute. Returns None if missing."""
    try:
        return node.getAttribute(f"data-{key}")
    except Exception:
        return None


# If the page still has the old charm section, turn it into the new charm builder.
_old = document.querySelector(".charm-options")
if _old is not None and _old.id != "charm-options":
    _old.id = "charm-options"
    _lbl = _old.previousElementSibling
    if _lbl is not None: _lbl.innerText = "Charms (+₱10 each, up to 3 of each)"


def label_color(color, kind):
    """Pick a readable letter color for a bead."""
    if kind == "Pearl-like": return "#26213c"
    h = color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#26213c" if (0.299 * r + 0.587 * g + 0.114 * b) > 165 else "#ffffff"


def bead(color, kind="Acrylic", label=""):
    return f'<div class="bead tex-{kind}" style="--c:{color};--t:{label_color(color, kind)}">{esc(label)}</div>'


def charm_html(symbol): return f'<div class="bead charm">{symbol}</div>'


async def toast(text):
    t = el("toast")
    t.innerText, t.className = text, "show"
    await asyncio.sleep(2)
    t.className = ""


# ---------- Cart State & Calculations ----------
def save(): window.localStorage.setItem(KEY, json.dumps(state["cart"]))


def load():
    try:
        raw = window.localStorage.getItem(KEY)
        if raw: state["cart"] = json.loads(raw)
    except Exception:
        state["cart"] = []


def totals():
    qty = sum(i["qty"] for i in state["cart"])
    sub = sum(i["unit"] * i["qty"] for i in state["cart"])
    disc = sub * 0.10 if qty >= 3 else 0
    fee = int(el("method").value)
    return qty, sub, disc, fee, sub - disc + (fee if state["cart"] else 0)


def add_item(title, detail, unit, qty, color):
    for it in state["cart"]:
        if it["title"] == title and it["detail"] == detail and it["unit"] == unit and it.get("color") == color:
            it["qty"] += qty
            break
    else:
        state["cart"].append({"title": title, "detail": detail, "unit": unit, "qty": qty, "color": color})
    save(); render_cart()


def render_cart():
    cart = state["cart"]
    if not cart:
        el("cart-list").innerHTML = '<li class="muted">Your cart is empty. Add a bracelet to start.</li>'
    else:
        el("cart-list").innerHTML = "".join(
            f'<li><span><b>{esc(it["title"])}</b><br><span class="muted">{esc(it["detail"])}</span></span>'
            f'<b>{peso(it["unit"] * it["qty"])}</b>'
            f'<span class="qty"><button data-act="dec" data-i="{i}">-</button>{it["qty"]}'
            f'<button data-act="inc" data-i="{i}">+</button></span>'
            f'<button class="rm" data-act="rm" data-i="{i}">Remove</button></li>'
            for i, it in enumerate(cart)
        )
    qty, sub, disc, fee, total = totals()
    el("cart-count").innerText = str(qty)
    t = f'<div><span>Subtotal</span><span>{peso(sub)}</span></div>'
    if disc: t += f'<div><span>Bundle discount (10%)</span><span>-{peso(disc)}</span></div>'
    if fee and cart: t += f'<div><span>Delivery</span><span>{peso(fee)}</span></div>'
    t += f'<div class="grand"><span>Total</span><span>{peso(total)}</span></div>'
    el("totals").innerHTML = t


# ---------- Catalog ----------
def render_catalog():
    el("catalog").innerHTML = "".join(
        f'<article class="card prod"><img class="pimg" src="{p["image"]}" alt="{p["title"]}" loading="lazy"><h3>{p["title"]}</h3>'
        f'<p>{p["desc"]}</p><div class="row"><b>{peso(p["unit"])}</b><button class="btn" data-id="{p["id"]}">Add</button></div></article>'
        for p in CATALOG if state["tag"] in ("all", p["tag"])
    )


@when("click", "#filters")
def on_filter(event):
    tag = data(event.target, "tag")
    if tag:
        state["tag"] = tag
        for f in document.querySelectorAll(".filter"):
            f.classList.toggle("on", data(f, "tag") == tag)
        render_catalog()


@when("click", "#catalog")
def on_catalog(event):
    pid = data(event.target, "id")
    if pid:
        p = next(x for x in CATALOG if x["id"] == int(pid))
        add_item(p["title"], p["desc"], p["unit"], 1, p["colors"][0])
        asyncio.ensure_future(toast(f'{p["title"]} added to cart'))


# ---------- Builder & Preview ----------
def clean_name():
    return "".join(c for c in el("name").value.upper() if c.isalpha() or c == " ").strip()


def clamp_pos(p, n):
    if p == "bottom": return p
    try: return str(max(0, min(int(p), n)))
    except ValueError: return "bottom"


def describe(p, name):
    if p == "bottom": return "at the bottom"
    i = int(p)
    if i == 0 or not name: return "before name"
    ch = name[min(i, len(name)) - 1]
    return "after space" if ch == " " else f"after {ch}"


def render_charms():
    """Draw the charm steppers and one placement dropdown per charm copy."""
    word = clean_name() or "BEADS"
    n = len(word)
    opts = [("0", "Before name")]
    opts += [(str(i + 1), "After space" if ch == " " else f"After {ch} (letter {i + 1})") for i, ch in enumerate(word)]
    opts += [("bottom", "Bottom of bracelet")]

    rows = []
    for sym, label in CHARMS:
        lst = state["charms"][sym]
        for k in range(len(lst)): lst[k] = clamp_pos(lst[k], n)
        slots = "".join(
            f'<label class="charm-slot"><span>Charm {k + 1}</span><select data-sym="{sym}" data-k="{k}" aria-label="{label} {k + 1} position">'
            + "".join(f'<option value="{v}"{" selected" if v == p else ""}>{esc(t)}</option>' for v, t in opts)
            + '</select></label>'
            for k, p in enumerate(lst)
        )
        rows.append(
            f'<div class="charm-item"><div class="charm-head">'
            f'<span class="charm-name"><b>{sym}</b> {label}</span>'
            f'<span class="stepper">'
            f'<button type="button" data-act="dec" data-sym="{sym}" aria-label="Remove one {label}"{" disabled" if not lst else ""}>&minus;</button>'
            f'<output>{len(lst)}</output>'
            f'<button type="button" data-act="inc" data-sym="{sym}" aria-label="Add one {label}"{" disabled" if len(lst) >= MAX_EACH else ""}>+</button>'
            f'</span></div>{slots}</div>'
        )
    box = el("charm-options")
    if box is not None:
        box.innerHTML = "".join(rows)


def current():
    name = clean_name()
    placed = [(s, p) for s, _ in CHARMS for p in state["charms"][s]]
    charm_list = [s for s, _ in placed]

    try: qty = max(1, min(50, int(el("qty").value.strip() or 1)))
    except ValueError: qty = 1

    bt = el("bead").value
    unit = BASE + BEAD_PRICE[bt] + LETTER * len(name.replace(" ", "")) + CHARM * len(charm_list)
    return {"name": name, "bead": bt, "charms": charm_list, "placed": placed,
            "qty": qty, "unit": unit, "color": state["color"]}


def build_ring(word, col, kind, charms, box):
    """Bracelet ring. charms is a list of (symbol, position) where position is
    '0'..'n' (index among the letters) or 'bottom'."""
    n = 0

    def filler():
        nonlocal n
        c = MIX[(n // 2) % len(MIX)] if kind == "Mixed" and n % 2 else col
        n += 1
        return bead(c, kind)

    parts = [bead(col, kind, ch if ch != " " else "") for ch in word]
    at = {i: [] for i in range(len(parts) + 1)}
    bottom = []
    for sym, p in charms:
        if p == "bottom": bottom.append(charm_html(sym))
        else: at[max(0, min(int(p), len(parts)))].append(charm_html(sym))

    core = list(at[0])
    for i, part in enumerate(parts):
        core.append(part)
        core += at[i + 1]

    count = max(18, len(core) + len(bottom) + 3)
    fill = [filler() for _ in range(count - len(core) - len(bottom))]
    h = len(fill) // 2
    items = core + fill[:h] + bottom + fill[h:]

    step = 2 * math.pi / count
    radius = box / 2 - 24
    d = max(20, min(34, 2 * math.pi * radius / count * 0.88))

    slots = []
    for i, item_html in enumerate(items):
        a = -math.pi / 2 + (i - (len(core) - 1) / 2) * step   # name centered at top
        x, y = math.cos(a) * radius, math.sin(a) * radius
        slots.append(
            f'<div class="slot" style="left:calc(50% + {x:.1f}px);top:calc(50% + {y:.1f}px)">{item_html}</div>'
        )
    return f'<div class="ring" style="--d:{d:.1f}px">{"".join(slots)}</div>'


def refresh_preview():
    b = current()
    word = b["name"] or "BEADS"
    el("preview").innerHTML = build_ring(word, b["color"], b["bead"], b["placed"], 240)
    el("summary").innerText = f'{b["bead"]} beads, {len(b["charms"])} charm(s), {peso(b["unit"])} each'
    el("price").innerText = peso(b["unit"] * b["qty"])


@when("input", "#name")
def on_name(event): render_charms(); refresh_preview()


@when("input", "#qty")
def on_qty(event): refresh_preview()


@when("change", "#qty")
def on_qty_change(event): refresh_preview()


@when("change", "#bead")
def on_bead(event): refresh_preview()


@when("click", "#charm-options")
def on_charm_click(event):
    t = event.target
    act, sym = data(t, "act"), data(t, "sym")
    if not act or not sym:
        return
    lst = state["charms"][sym]
    if act == "inc" and len(lst) < MAX_EACH:
        lst.append(str(len(clean_name() or "BEADS") // 2))
    elif act == "dec" and lst:
        lst.pop()
    render_charms(); refresh_preview()


@when("change", "#charm-options")
def on_charm_pos(event):
    t = event.target
    sym, k = data(t, "sym"), data(t, "k")
    if sym and k is not None:
        state["charms"][sym][int(k)] = t.value
        refresh_preview()


@when("click", ".swatches")
def on_swatch(event):
    if event.target.classList.contains("swatch"):
        state["color"] = data(event.target, "color")
        for s in document.querySelectorAll(".swatch"):
            s.classList.toggle("on", s is event.target)
        refresh_preview()


@when("click", "#add")
def on_add(event):
    b = current()
    m = el("build-msg")
    if not b["name"]:
        m.className, m.innerText = "msg bad", "Type a name or word first."
        return
    extras = ", ".join(f"{s} {describe(p, b['name'])}" for s, p in b["placed"])
    detail = f'{b["bead"]} beads' + (f" + {extras}" if extras else "")
    add_item(f'Custom: {b["name"]}', detail, b["unit"], b["qty"], b["color"])
    m.className = "msg"
    asyncio.ensure_future(toast(f'"{b["name"]}" added to cart'))


# ---------- Cart Actions & Checkout ----------
@when("click", "#cart-list")
def on_cart(event):
    act = data(event.target, "act")
    if act:
        i = int(data(event.target, "i"))
        if act == "inc": state["cart"][i]["qty"] += 1
        elif act == "dec": state["cart"][i]["qty"] = max(1, state["cart"][i]["qty"] - 1)
        elif act == "rm": state["cart"].pop(i)
        save(); render_cart()


@when("click", "#clear")
def on_clear(event):
    state["cart"].clear(); save(); render_cart()


@when("change", "#method")
def on_method(event): render_cart()


@when("submit", "#order-form")
def on_order(event):
    event.preventDefault()
    cust, contact = el("cust").value.strip(), el("contact").value.strip()
    el("e-cust").innerText = "" if cust else "Enter your name."
    el("e-contact").innerText = "" if ("@" in contact and "." in contact.split("@")[-1]) or len("".join(c for c in contact if c.isdigit())) >= 10 else "Enter a valid mobile number or email."
    m = el("order-msg")
    if not state["cart"]:
        m.className, m.innerText = "msg bad", "Your cart is empty. Add a bracelet first."
        return
    if not cust or el("e-contact").innerText:
        m.className = "msg"
        return
    _, _, _, _, total = totals()
    ref = f"BL-{random.randint(1000, 9999)}"
    note = el("note").value.strip()
    items = "".join(f'<br>{esc(i["title"])} x{i["qty"]}' for i in state["cart"])
    m.className = "msg ok"
    m.innerHTML = (f"<b>Order {ref} received. Thank you, {esc(cust)}!</b>{items}<br>Total: <b>{peso(total)}</b>"
                   + (f"<br>Gift note: {esc(note)}" if note else "")
                   + f"<br>We will contact you at {esc(contact)}.")
    state["cart"].clear(); save(); render_cart()


# ---------- Init ----------
el("hero-strand").innerHTML = build_ring("BEADSLET", "#d98ba6", "Acrylic", [], 280)
load(); render_catalog(); render_charms(); refresh_preview(); render_cart()
