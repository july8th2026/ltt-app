# App Icon Design Guide — LTTStudio VideoBot

> **TikTok requirement:** 1024×1024 PNG, square, no rounded corners
> (TikTok and OS will apply rounding automatically)

---

## 🎯 What you need

```
Final output: lttstudio-icon-1024.png
Format:       PNG (with or without transparency)
Size:         exactly 1024 × 1024 pixels
Color mode:   sRGB
File size:    < 5 MB
```

---

## 🎨 Design Direction

You already have a beautiful base logo at `E:\logo moi\logoLTT.png`. The current logo features:
- LTT diamond shape with circuit board pattern
- Cyan/blue neon glow
- Tech aesthetic
- Transparent background

### Option A — Keep existing logo (recommended, fastest)

**Steps:**
1. Open `E:\logo moi\logoLTT.png` in Photoshop, GIMP, or Figma
2. Verify it's square — if not, crop to square (1:1 ratio)
3. Resize to **1024 × 1024 pixels** (Image → Image Size in Photoshop)
4. Use "Bicubic Smoother" for upscaling if original is smaller
5. **Add background fill** (TikTok displays icons on dark backgrounds — transparency may make logo look weird):
   - Recommended: dark navy (#0D1B2A) or pure black (#000000) background
   - This makes the cyan glow pop more
6. Export as PNG (Save for Web in Photoshop)
7. Save as `lttstudio-icon-1024.png`

### Option B — Online tools (no software needed)

1. Go to [favicon.io](https://favicon.io/favicon-converter/) or [iloveimg.com/resize-image](https://www.iloveimg.com/resize-image)
2. Upload `logoLTT.png`
3. Resize to 1024×1024
4. Download

### Option C — AI generation (if existing logo doesn't fit square crop)

Prompt for Midjourney / DALL-E:
```
"App icon for 'LTTStudio', diamond shape with circuit board patterns,
glowing cyan and blue neon, futuristic tech aesthetic, dark navy background,
centered composition, sharp focus, professional app icon design, 1024x1024,
no text"
```

---

## ⚠️ Common Mistakes to Avoid

1. ❌ **Transparent background** → Logo invisible on TikTok's app card backgrounds
2. ❌ **Round/circular icon** → TikTok requires square (they round it for you)
3. ❌ **Text "LTTStudio" visible** → Too small to read at 64px (TikTok's display size)
4. ❌ **More than 90% of canvas filled** → Leave 10-15% padding around the logo
5. ❌ **Compressed JPEG quality** → Use PNG for sharp edges
6. ❌ **Wrong aspect ratio** → Must be exactly 1:1 (1024×1024)

---

## ✅ Quality Check

Before submitting, view your icon at multiple sizes to ensure clarity:

```
1024×1024  → Full quality (TikTok upload)
512×512    → App store size
256×256    → Web display
128×128    → Tab/favorite icon
64×64      → TikTok inline (most common!)
32×32      → Browser tab
```

The LTT diamond should still be **recognizable at 64×64**. If it becomes a blur, simplify the design.

---

## 📁 Where to put the final file

Save to:
```
D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook\docs\tiktok-submission\lttstudio-icon-1024.png
```

Also upload to website:
```
D:\CODE AI\BOT UP FB + TikTok\lttstudio-web\assets\images\logo\icon-1024.png
```

Then update website meta tags:
```html
<link rel="apple-touch-icon" href="/assets/images/logo/icon-1024.png" />
```

---

## 🔗 References

- [TikTok app icon guidelines](https://developers.tiktok.com/doc/branding-guidelines)
- [Apple Human Interface — App Icons](https://developer.apple.com/design/human-interface-guidelines/app-icons)
- Free 1024×1024 icon validator: [realfavicongenerator.net](https://realfavicongenerator.net)
