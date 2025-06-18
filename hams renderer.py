import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import random
import math
import time
import numpy as np

WIDTH, HEIGHT = 600, 600
FOV = 500

COLOR_PALETTE = [
    (230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200),
    (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230),
    (255, 182, 193), (138, 43, 226), (255, 105, 180), (199, 21, 133),
    (123, 104, 238), (216, 191, 216), (255, 192, 203), (147, 112, 219),
    (0, 255, 127), (255, 69, 0), (173, 255, 47), (255, 20, 147),
    (75, 0, 130), (0, 255, 255), (255, 140, 0), (255, 99, 71)
]

SHAPES = ['circle', 'rectangle', 'triangle']

class ZoomPanCanvas(tk.Canvas):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self.bind("<ButtonPress-1>", self.start_pan)
        self.bind("<B1-Motion>", self.do_pan)
        self.bind("<ButtonPress-3>", self.start_rotate)
        self.bind("<B3-Motion>", self.do_rotate)
        self.bind("<MouseWheel>", self.do_zoom)
        self.last_x = 0
        self.last_y = 0
        self.redraw_callback = None

    def start_pan(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def do_pan(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        if self.redraw_callback:
            self.redraw_callback(dx, dy, 0)
        self.last_x = event.x
        self.last_y = event.y

    def start_rotate(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def do_rotate(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        if self.redraw_callback:
            self.redraw_callback(0, 0, dy)
        self.last_x = event.x
        self.last_y = event.y

    def do_zoom(self, event):
        if self.redraw_callback:
            self.redraw_callback(0, 0, 0, event.delta)

class VisualizerApp:
    def __init__(self, root):
        self.root = root
        self.canvas = ZoomPanCanvas(root, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.canvas.redraw_callback = self.transform_view

        self.entry = tk.Entry(root)
        self.entry.pack()

        self.render_button = tk.Button(root, text="Render", command=self.set_word)
        self.render_button.pack()

        self.status = tk.Label(root, text="Type a word and click Render")
        self.status.pack()

        self.fps_label = tk.Label(root, text="FPS: 0")
        self.fps_label.pack()

        self.word = ""
        self.image = None
        self.photo = None

        self.cam_x = 0
        self.cam_y = 0
        self.cam_z = -400
        self.cam_rot_x = 0
        self.cam_rot_y = 0
        self.zoom = 1.0
        self.layers = 5
        self.shape_data = []

        self.root.bind("<KeyPress-w>", lambda e: self.transform_view(0, -10, 0))
        self.root.bind("<KeyPress-s>", lambda e: self.transform_view(0, 10, 0))
        self.root.bind("<KeyPress-a>", lambda e: self.transform_view(-10, 0, 0))
        self.root.bind("<KeyPress-d>", lambda e: self.transform_view(10, 0, 0))
        self.root.bind("<KeyPress-q>", lambda e: self.transform_view(0, 0, -10))
        self.root.bind("<KeyPress-e>", lambda e: self.transform_view(0, 0, 10))
        self.root.bind("<Left>", lambda e: self.rotate_view(-5, 0))
        self.root.bind("<Right>", lambda e: self.rotate_view(5, 0))
        self.root.bind("<Up>", lambda e: self.rotate_view(0, -5))
        self.root.bind("<Down>", lambda e: self.rotate_view(0, 5))

    def set_word(self):
        self.word = self.entry.get().strip().lower()
        self.cam_x = 0
        self.cam_y = 0
        self.cam_z = -400
        self.cam_rot_x = 0
        self.cam_rot_y = 0
        self.status.config(text=f"Visualizing '{self.word}'")
        self.generate_shapes()
        self.root.focus()
        self.redraw()

    def generate_shapes(self):
        self.shape_data.clear()
        base_seed = sum(ord(c) for c in self.word) if self.word else 42
        random_seed = int(time.time() * 1000)
        combined_seed = base_seed + random_seed
        random.seed(combined_seed)

        for layer in range(self.layers):
            base_color = COLOR_PALETTE[layer % len(COLOR_PALETTE)]
            if self.word == "infinite":
                self.shape_data.append(("infinite", layer))
            else:
                num_points = 100 + random.randint(-20, 20)
                shape_size_base = 20 + layer * 5
                space_size = 400
                for _ in range(num_points):
                    x = random.uniform(-space_size, space_size)
                    y = random.uniform(-space_size, space_size)
                    z = random.uniform(layer * 50, layer * 50 + space_size)
                    size = shape_size_base * random.uniform(0.5, 1.5)
                    shape_type = random.choice(SHAPES)
                    color = tuple(
                        min(255, max(0, int(c + random.randint(-60, 60))))
                        for c in base_color
                    )
                    self.shape_data.append((shape_type, x, y, z, size, color))

    def project_point(self, x, y, z):
        x -= self.cam_x
        y -= self.cam_y
        z += self.cam_z

        cos_rx, sin_rx = math.cos(math.radians(self.cam_rot_x)), math.sin(math.radians(self.cam_rot_x))
        y, z = y * cos_rx - z * sin_rx, y * sin_rx + z * cos_rx

        cos_ry, sin_ry = math.cos(math.radians(self.cam_rot_y)), math.sin(math.radians(self.cam_rot_y))
        x, z = x * cos_ry + z * sin_ry, -x * sin_ry + z * cos_ry

        scale = FOV / (FOV + z) if (FOV + z) != 0 else 1
        sx = WIDTH // 2 + x * scale * self.zoom
        sy = HEIGHT // 2 + y * scale * self.zoom
        return sx, sy, scale

    def redraw(self):
        start_time = time.time()

        image = Image.new("RGB", (WIDTH, HEIGHT), "white")
        draw = ImageDraw.Draw(image)

        for item in self.shape_data:
            if item[0] == "infinite":
                continue
            else:
                shape_type, x, y, z, size, color = item
                sx, sy, scale = self.project_point(x, y, z)
                screen_size = size * scale
                if 0 <= sx <= WIDTH and 0 <= sy <= HEIGHT and screen_size > 1:
                    if shape_type == 'circle':
                        draw.ellipse([sx - screen_size, sy - screen_size, sx + screen_size, sy + screen_size], outline=color, width=2)
                    elif shape_type == 'rectangle':
                        draw.rectangle([sx - screen_size, sy - screen_size, sx + screen_size, sy + screen_size], outline=color, width=2)
                    elif shape_type == 'triangle':
                        points = [
                            (sx, sy - screen_size),
                            (sx - screen_size, sy + screen_size),
                            (sx + screen_size, sy + screen_size),
                        ]
                        draw.polygon(points, outline=color)

        draw.text((10, HEIGHT - 30), "Hams Renderer", fill=(0, 0, 0))
        draw.text((10, HEIGHT - 15), "Model: HOV 0.1", fill=(0, 0, 0))

        self.image = image
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        elapsed = time.time() - start_time
        fps = 1.0 / elapsed if elapsed > 0 else 0
        self.fps_label.config(text=f"FPS: {fps:.2f}")

    def transform_view(self, dx, dy, dz, zoom_delta=0):
        self.cam_x += dx
        self.cam_y += dy
        self.cam_z += dz
        self.zoom += zoom_delta / 120 * 0.1
        self.zoom = max(0.1, min(self.zoom, 10.0))
        self.redraw()

    def rotate_view(self, dx, dy):
        self.cam_rot_y += dx
        self.cam_rot_x += dy
        self.redraw()

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizerApp(root)
    root.mainloop()
