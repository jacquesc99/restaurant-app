import qrcode
from qrcode.image.styled import StyledPilImage
from qrcode.image.styles.moduledrivers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidColorMask

# 1. Configuration - Change your settings here
URL_DATA = "https://allergens-at-restaurants.onrender.com/menu/ambrogio15-pb"
LOGO_PATH = "logo.png"       # Your logo file name (must be in the same folder)
OUTPUT_NAME = "my_brand_qr.png"

# Colors in RGB format (0-255)
# Example: Dark Navy Blue foreground on a crisp white background
QR_COLOR_RGB = (10, 34, 64)
BG_COLOR_RGB = (255, 255, 255)

# 2. Initialize QR Code with High Error Correction
# ERROR_CORRECT_H allows up to 30% of the code to be covered by your logo
qr = qrcode.QRCode(
    version=None, # Automatically determines size based on data
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,  # Controls pixel resolution scale
    border=4      # Standard clear margin around the QR code
)
qr.add_data(URL_DATA)
qr.make(fit=True)

# 3. Apply custom styles, colors, and embed the logo completely offline
custom_qr_image = qr.make_image(
    image_factory=StyledPilImage,
    module_drawer=RoundedModuleDrawer(), # Makes the dots smooth and rounded
    color_mask=SolidColorMask(back_color=BG_COLOR_RGB, front_color=QR_COLOR_RGB),
    embeded_image_path=LOGO_PATH # Automatically resizes and centers your logo
)

# 4. Save the finished product to your hard drive
custom_qr_image.save(OUTPUT_NAME)
print(f"Success! Your custom QR code has been saved locally as '{OUTPUT_NAME}'")
