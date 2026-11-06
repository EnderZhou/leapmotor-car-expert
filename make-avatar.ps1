Add-Type -AssemblyName System.Drawing
$destination = 'outputs\leapmotor-car-expert-v0.1\source\leapmotor-car-expert\avatar.png'
$bitmap = New-Object System.Drawing.Bitmap(512, 512, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::FromArgb(21, 61, 54))

$outerBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(39, 91, 77))
$pageBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(244, 238, 219))
$inkPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(21, 61, 54), 13)
$accentPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(244, 238, 219), 11)
$wheelBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(21, 61, 54))
$graphics.FillEllipse($outerBrush, 34, 34, 444, 444)

# Open book mark: knowledge source, not a vehicle-brand logo.
$book = New-Object System.Drawing.Drawing2D.GraphicsPath
$book.AddLine(128, 112, 235, 130)
$book.AddLine(235, 130, 235, 232)
$book.AddBezier(235, 232, 200, 210, 158, 204, 128, 212)
$book.AddLine(128, 212, 128, 112)
$book.CloseFigure()
$graphics.FillPath($pageBrush, $book)
$book2 = New-Object System.Drawing.Drawing2D.GraphicsPath
$book2.AddLine(277, 130, 384, 112)
$book2.AddLine(384, 112, 384, 212)
$book2.AddBezier(384, 212, 354, 204, 312, 210, 277, 232)
$book2.AddLine(277, 232, 277, 130)
$book2.CloseFigure()
$graphics.FillPath($pageBrush, $book2)
$graphics.DrawLine($accentPen, 256, 136, 256, 225)

# Car silhouette below the open book.
$car = New-Object System.Drawing.Drawing2D.GraphicsPath
$car.AddLine(103, 328, 124, 286)
$car.AddBezier(124, 286, 140, 260, 164, 248, 194, 247)
$car.AddLine(194, 247, 309, 247)
$car.AddBezier(309, 247, 343, 247, 363, 263, 378, 288)
$car.AddLine(378, 288, 409, 324)
$car.AddLine(409, 324, 409, 362)
$car.AddLine(409, 362, 366, 362)
$car.AddLine(146, 362, 103, 362)
$car.CloseFigure()
$graphics.FillPath($pageBrush, $car)
$graphics.DrawLine($inkPen, 187, 258, 160, 300)
$graphics.DrawLine($inkPen, 160, 300, 353, 300)
$graphics.FillEllipse($wheelBrush, 148, 337, 48, 48)
$graphics.FillEllipse($wheelBrush, 320, 337, 48, 48)
$graphics.FillEllipse($pageBrush, 162, 351, 20, 20)
$graphics.FillEllipse($pageBrush, 334, 351, 20, 20)

$bitmap.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
$outerBrush.Dispose()
$pageBrush.Dispose()
$inkPen.Dispose()
$accentPen.Dispose()
$wheelBrush.Dispose()
