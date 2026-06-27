import hashlib
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


LIVE_CATEGORIES = [
    "Fashion",
    "Electronics",
    "Food",
    "Health",
    "Home & Living",
    "Salon & Spa",
    "Beauty & Cosmetics",
    "Gifts & Specialty",
    "Entertainment",
    "Vehicles & Auto",
    "Travel",
    "Education",
    "Fitness",
    "Professional Services",
    "Grocery",
    "Lifestyle & Hobbies",
    "Nicotine",
    "Financial & Legal Services",
    "Logistics",
    "Mother & Baby",
]

LIVE_BUSINESSES = [
    {
        "slug": "burger-express",
        "name": "Burger Express",
        "category": "Food",
        "branches": [
            ("Clifton Branch", "Block 5", "22", "75600", "Karachi", "24.813800", "67.029900"),
            ("DHA Branch", "Phase 6", "14", "75500", "Karachi", "24.799300", "67.046500"),
        ],
        "offers": [
            ("percentage_bill", "Family Feast Deal", "30% off the entire bill.", "30.00", None, None, None),
            ("item", "Classic Burger Combo", "Burger combo at a special price.", "42.86", "Classic Burger Combo", "7.00", "4.00"),
        ],
    },
    {
        "slug": "style-studio",
        "name": "Style Studio",
        "category": "Fashion",
        "branches": [
            ("Saddar Branch", "MA Jinnah Road", "101", "74400", "Karachi", "24.854600", "67.011200"),
        ],
        "offers": [
            ("percentage_bill", "Season Sale", "25% off on all clothing.", "25.00", None, None, None),
            ("percentage_bill", "Weekend Special", "15% off this weekend.", "15.00", None, None, None),
        ],
    },
    {
        "slug": "techhive",
        "name": "TechHive",
        "category": "Electronics",
        "branches": [
            ("Forum Branch", "Khayaban-e-Jami", "45", "75350", "Karachi", "24.829400", "67.067800"),
            ("North Nazimabad", "Block H", "8", "74600", "Karachi", "24.936700", "67.036900"),
        ],
        "offers": [
            ("percentage_bill", "Gadget Week", "20% off accessories.", "20.00", None, None, None),
            ("item", "Wireless Earbuds", "Premium earbuds offer.", "33.33", "Wireless Earbuds", "60.00", "40.00"),
        ],
    },
    {
        "slug": "medcare-plus",
        "name": "MedCare Plus",
        "category": "Health",
        "branches": [
            ("Gulshan Branch", "Main Avenue", "3", "75300", "Karachi", "24.920100", "67.082100"),
        ],
        "offers": [
            ("percentage_bill", "Wellness Checkup", "10% off health screenings.", "10.00", None, None, None),
        ],
    },
    {
        "slug": "cozynest",
        "name": "CozyNest",
        "category": "Home & Living",
        "branches": [
            ("Bahria Branch", "Commercial Ave", "18", "75500", "Karachi", "24.852700", "67.211200"),
        ],
        "offers": [
            ("percentage_bill", "Home Refresh Sale", "35% off selected decor.", "35.00", None, None, None),
            ("item", "Luxury Cushion Set", "Home comfort bundle.", "40.00", "Luxury Cushion Set", "50.00", "30.00"),
        ],
    },
    {
        "slug": "bliss-spa",
        "name": "Bliss Spa",
        "category": "Salon & Spa",
        "branches": [
            ("Boat Basin Branch", "Boat Basin", "7", "75530", "Karachi", "24.813200", "67.034500"),
        ],
        "offers": [
            ("percentage_bill", "Relax Package", "20% off spa services.", "20.00", None, None, None),
        ],
    },
    {
        "slug": "glamour-box",
        "name": "Glamour Box",
        "category": "Beauty & Cosmetics",
        "branches": [
            ("Tariq Road Branch", "Tariq Road", "55", "75400", "Karachi", "24.875600", "67.059800"),
        ],
        "offers": [
            ("percentage_bill", "Beauty Bonanza", "28% off cosmetics.", "28.00", None, None, None),
            ("item", "Skincare Starter Kit", "Complete skincare bundle.", "37.50", "Skincare Starter Kit", "80.00", "50.00"),
        ],
    },
    {
        "slug": "gift-haven",
        "name": "Gift Haven",
        "category": "Gifts & Specialty",
        "branches": [
            ("PECHS Branch", "Allama Iqbal Road", "12", "75400", "Karachi", "24.869700", "67.074500"),
        ],
        "offers": [
            ("percentage_bill", "Gift Season Offer", "18% off gift items.", "18.00", None, None, None),
        ],
    },
    {
        "slug": "funzone-cinema",
        "name": "FunZone Cinema",
        "category": "Entertainment",
        "branches": [
            ("Ocean Mall Branch", "Clifton", "2", "75600", "Karachi", "24.801900", "67.030800"),
        ],
        "offers": [
            ("percentage_bill", "Movie Night Deal", "22% off movie tickets.", "22.00", None, None, None),
            ("item", "Popcorn Combo", "Large popcorn combo deal.", "25.00", "Popcorn Combo", "12.00", "9.00"),
        ],
    },
    {
        "slug": "drivemaster-auto",
        "name": "DriveMaster Auto",
        "category": "Vehicles & Auto",
        "branches": [
            ("SITE Branch", "Industrial Area", "44", "75700", "Karachi", "24.885500", "66.982300"),
        ],
        "offers": [
            ("percentage_bill", "Service Special", "12% off car service.", "12.00", None, None, None),
        ],
    },
    {
        "slug": "powerfit-gym",
        "name": "PowerFit Gym",
        "category": "Fitness",
        "branches": [
            ("Defence Branch", "Badar Commercial", "9", "75500", "Karachi", "24.791800", "67.063400"),
            ("Gulistan Branch", "Gulistan-e-Johar", "21", "75290", "Karachi", "24.903800", "67.114500"),
        ],
        "offers": [
            ("percentage_bill", "New Member Offer", "40% off first month.", "40.00", None, None, None),
            ("percentage_bill", "Personal Training", "15% off PT sessions.", "15.00", None, None, None),
        ],
    },
    {
        "slug": "greenbasket",
        "name": "GreenBasket",
        "category": "Grocery",
        "branches": [
            ("Johar Branch", "Rashid Minhas Road", "66", "75290", "Karachi", "24.912300", "67.122100"),
        ],
        "offers": [
            ("percentage_bill", "Fresh Produce Deal", "16% off fresh groceries.", "16.00", None, None, None),
            ("item", "Organic Fruit Box", "Weekly organic fruit box.", "30.00", "Organic Fruit Box", "25.00", "17.50"),
        ],
    },
    {
        "slug": "learnhub",
        "name": "LearnHub",
        "category": "Education",
        "branches": [
            ("Online Center", "II Chundrigar Road", "33", "74000", "Karachi", "24.847200", "67.001800"),
        ],
        "offers": [
            ("percentage_bill", "Course Bundle", "24% off online courses.", "24.00", None, None, None),
        ],
    },
]

DEMO_BUSINESS_PASSWORD = "DemoPass123!"


def _color_from_key(key: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(key.encode()).hexdigest()
    return (
        64 + int(digest[0:2], 16) % 176,
        64 + int(digest[2:4], 16) % 176,
        64 + int(digest[4:6], 16) % 176,
    )


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_seed_image(title: str, subtitle: str, filename: str) -> ContentFile:
    width, height = 800, 800
    background = _color_from_key(title)
    accent = _color_from_key(subtitle or title + "-accent")

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, width - 40, height - 40), fill=accent, outline=(255, 255, 255), width=4)
    draw.ellipse((120, 120, width - 120, height - 120), fill=background, outline=(255, 255, 255), width=3)

    title_font = _load_font(52)
    subtitle_font = _load_font(30)
    draw.multiline_text(
        (80, 300),
        title,
        fill=(255, 255, 255),
        font=title_font,
        spacing=8,
    )
    if subtitle:
        draw.text((80, 520), subtitle, fill=(240, 240, 240), font=subtitle_font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=filename)
