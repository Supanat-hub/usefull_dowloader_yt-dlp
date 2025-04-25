import customtkinter as ctk
from PIL import Image
from yt_dlp import YoutubeDL
import requests
import io
import threading
import os
from tkinter import filedialog
import shutil
import re

def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)  # ลบอักขระต้องห้าม
    name = name.strip().strip('.')            # ตัดช่องว่าง/จุดหน้า-ท้าย
    return name[:100] or "video"              # จำกัดความยาว และ fallback

video_title = ["output_temp"]  # ใช้ list เพื่อให้เปลี่ยนจากในฟังก์ชันได้

def save_as(filepath):
    if not os.path.exists(filepath):
        result_label.configure(text="ไม่พบไฟล์ที่โหลด ❌")
        return

    new_path = filedialog.asksaveasfilename(
        initialfile=sanitize_filename(video_title[0]),
        defaultextension=os.path.splitext(filepath)[1],
        filetypes=[("Video/Audio", "*.*")]
    )
    result_label.configure(text=f"บันทึกที่:\n{new_path}")
    app.after(10000, lambda: result_label.configure(text=""))  # ลบข้อความหลัง 10 วินาที

    if new_path:
        shutil.move(filepath, new_path)
    else:
        result_label.configure(text="ยกเลิกการเลือกไฟล์")

merging = [False]

def animate_merging_text():
    dots = ["", ".", ". .", ". . ."]
    index = [0]

    def loop():
        if not merging[0]:
            return
        result_label.configure(text=f"กำลังรวมไฟล์{dots[index[0]]}")
        index[0] = (index[0] + 1) % len(dots)
        app.after(500, loop)

    loop()

ctk.set_default_color_theme("blue")
ctk.set_appearance_mode("System")

app = ctk.CTk()
app.title("YouTube Downloader")
app.geometry("900x400")

default_img = ctk.CTkImage(
    light_image=Image.open("img/default_thumb.png"),
    size=(360, 200)
)

# แบ่งซ้าย-ขวา
main_frame = ctk.CTkFrame(app)
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

left_frame = ctk.CTkFrame(main_frame, width=600)
left_frame.pack(side="left", fill="both", expand=True, padx=(0,10))

right_frame = ctk.CTkFrame(main_frame, width=400)
right_frame.pack(side="right", fill="both", expand=True)

# 🎬 ฝั่งซ้าย: แสดงรูป + รายละเอียดวิดีโอ
thumb_label = ctk.CTkLabel(left_frame, text="", image=default_img)
thumb_label.image = default_img  # เก็บอ้างอิงไว้
thumb_label.pack(pady=(10,5))

title_label = ctk.CTkLabel(left_frame, text="", font=("Arial", 15), wraplength=600, anchor="w", justify="left")
title_label.pack(pady=(5,2))

info_label = ctk.CTkLabel(left_frame, text="", font=("Arial", 12), wraplength=600, anchor="w", justify="left")
info_label.pack(pady=(2,5))

# 🧾 ฝั่งขวา: ฟอร์มควบคุม
url_frame = ctk.CTkFrame(right_frame)
url_frame.pack(pady=(20, 10), padx=10, fill="x")

url_entry = ctk.CTkEntry(url_frame, placeholder_text="วาง URL ที่นี่")
url_entry.pack(side="left", fill="x", expand=True)
last_url = [None]  # ใช้ list เพื่อให้แก้ได้ภายใน nested function

def paste_url():
    try:
        text = app.clipboard_get()
        url_entry.delete(0, ctk.END)
        url_entry.insert(0, text)
        delayed_fetch() # เรียกให้ดึงข้อมูลอัตโนมัติหลังวาง
    except Exception as e:
        result_label.configure(text="⚠️ ไม่สามารถวางจากคลิปบอร์ดได้")

paste_button = ctk.CTkButton(url_frame, text="วาง", width=80, command=paste_url)
paste_button.pack(side="right", padx=(5, 0))

def delayed_fetch(event=None):
    current_url = url_entry.get()
    last_url[0] = current_url
    app.after(1000, check_if_url_stable)  # หน่วง 1 วินาที

def check_if_url_stable():
    current = url_entry.get()
    if current == last_url[0] and current.strip() != "":
        fetch_formats()

url_entry.bind("<KeyRelease>", delayed_fetch)     # เวลาพิมพ์
url_entry.bind("<<Paste>>", delayed_fetch)        # เวลาวาง


dropdown = ctk.CTkOptionMenu(right_frame, values=[])
dropdown.set("รอการกรอกข้อมูล...")
dropdown.pack(pady=5, padx=10)

def download_selected():
    selected = dropdown.get()
    if "audio" in selected:
        download_audio()
    else:
        download_format()

download_btn = ctk.CTkButton(right_frame, text="ดาวน์โหลด", command=lambda: download_selected())
download_btn.pack(pady=(5,10), padx=10)

result_label = ctk.CTkLabel(right_frame, text="", text_color="gray")
result_label.pack(pady=5)

# 📥 ตัวแปร format
format_dict = {}

# 🎯 โหลดรูป thumbnail จาก URL
def load_thumbnail(url):
    try:
        response = requests.get(url)
        image_data = Image.open(io.BytesIO(response.content))
        photo = ctk.CTkImage(light_image=image_data, size=(360, 200))
        thumb_label.configure(image=photo)
        thumb_label.image = photo
    except Exception as e:
        thumb_label.configure(image=default_img)
        thumb_label.image = default_img
        result_label.configure(text="โหลด thumbnail ไม่สำเร็จ")

# 🔍 ดึงข้อมูล + กรอง format
def parse_format_id(fid):
    import re
    match = re.match(r"(\d+)", fid)
    return int(match.group(1)) if match else -1

def fetch_formats():
    url = url_entry.get()
    if not url:
        result_label.configure(text="กรุณาใส่ URL ก่อน")
        return

    def run():
        result_label.configure(text="กำลังดึงข้อมูล...")
        dropdown.set("")

        ydl_opts = {"quiet": True, "skip_download": True}
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                result_label.configure(text="❌ เว็บไซต์นี้อาจไม่รองรับหรือ URL ไม่ถูกต้อง")
                return

            # แสดงข้อมูลด้านซ้าย
            title_label.configure(text=info.get("title", ""))
            video_title[0] = info.get("title", "output_temp")
            details = f"ช่อง: {info.get('uploader', '-')}\nความยาว: {info.get('duration_string', '-')}"
            info_label.configure(text=details)
            thumb_url = info.get("thumbnail")
            if thumb_url:
                load_thumbnail(thumb_url)

            # เตรียม format ที่ดีที่สุดต่อแบบ
            formats = info.get('formats', [])
            format_dict.clear()
            choices = []

            best_video = {}
            best_audio = {}

            for f in formats:
                fid = f.get("format_id")
                ext = f.get("ext")
                if not fid or not ext:
                    continue
                fid_num = parse_format_id(fid)

                # Video-only
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('height'):
                    key = (f.get('height'), ext)
                    if key not in best_video or parse_format_id(best_video[key]['format_id']) < fid_num:
                        best_video[key] = f
                # Audio-only
                elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    key = ext
                    if key not in best_audio or parse_format_id(best_audio[key]['format_id']) < fid_num:
                        best_audio[key] = f


            for ext, f in best_audio.items():
                label = f"{ext} - audio"
                choices.append(label)
                format_dict[label] = f['format_id']

            for (res, ext), f in best_video.items():
                label = f"{ext} - {res}p"
                choices.append(label)
                format_dict[label] = f['format_id']

            app.after(0, lambda: update_dropdown(choices))

    threading.Thread(target=run).start()

def update_dropdown(choices):
    if choices:
        dropdown.configure(values=choices)
        dropdown.set("เลือกรูปแบบที่ต้องการ")
        result_label.configure(text="ดึงข้อมูลสำเร็จ")
    else:
        result_label.configure(text="ไม่พบรูปแบบที่รองรับ")

def download_audio():
    url = url_entry.get()
    selected = dropdown.get()
    if not url or selected not in format_dict:
        result_label.configure(text="กรุณาเลือกตัวเลือกให้ถูกต้อง")
        return

    format_id = format_dict[selected]
    result_label.configure(text="กำลังเริ่มดาวน์โหลดเสียง...")

    def fmt_speed(speed):
        if speed is None:
            return "-"
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024.0:
                return f"{speed:3.1f} {unit}"
            speed /= 1024.0
        return f"{speed:.1f} TB/s"

    def run():
        output_name = sanitize_filename(video_title[0]) + "_audio"
        filepath = [None]

        def progress_hook(d):
            if d['status'] == 'downloading':
                progress.pack(pady=(10, 0), padx=10, fill="x")
                downloaded = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                speed = d.get('speed', 0)

                if total_bytes > 0:
                    percent = downloaded / total_bytes
                    progress.set(percent)
                    result_label.configure(
                        text=f"กำลังดาวน์โหลด... {percent*100:.1f}% @ {fmt_speed(speed)}"
                    )
                else:
                    result_label.configure(
                        text=f"กำลังดาวน์โหลด... @ {fmt_speed(speed)}"
                    )
            elif d['status'] == 'finished':
                progress.set(1)
                filepath[0] = d.get('filename')
                progress.pack_forget()
                progress.set(0)
                result_label.configure(text="ดาวน์โหลดเสียงเสร็จ ✅")
                save_as(filepath[0])

        ydl_opts = {
            'quiet': True,
            'format': format_id,
            'outtmpl': output_name + '.%(ext)s',
            'progress_hooks': [progress_hook],
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        except Exception as e:
            if "[Errno 28] No space left on device" in str(e):
                result_label.configure(text="⚠️ พื้นที่เก็บข้อมูลไม่เพียงพอ")
            else:
                result_label.configure(text=f"❌ เกิดข้อผิดพลาดในการดาวน์โหลดเสียง: {e}")

    threading.Thread(target=run).start()

# ⬇️ ดาวน์โหลด
def download_format():
    url = url_entry.get()
    selected = dropdown.get()
    if not url or selected not in format_dict:
        result_label.configure(text="กรุณาเลือกตัวเลือกให้ถูกต้อง")
        return

    format_id = format_dict[selected]
    result_label.configure(text="กำลังเริ่ม...")

    def fmt_speed(speed):
        if speed is None:
            return "-"
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024.0:
                return f"{speed:3.1f} {unit}"
            speed /= 1024.0
        return f"{speed:.1f} TB/s"

    def run():
        output_name = "output_temp"
        filepath = [None]

        def progress_hook(d):
            if d['status'] == 'downloading':
                progress.pack(pady=(10, 0), padx=10, fill="x")
                downloaded = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                speed = d.get('speed', 0)

                if total_bytes > 0:
                    percent = downloaded / total_bytes
                    progress.set(percent)
                    result_label.configure(
                        text=f"กำลังดาวน์โหลด... {percent*100:.1f}% @ {fmt_speed(speed)}"
                    )
                else:

                    result_label.configure(
                        text=f"กำลังดาวน์โหลด... @ {fmt_speed(speed)}"
                    )
            elif d['status'] == 'finished':
                merging[0] = True
                animate_merging_text()
                progress.set(1)
                filepath[0] = d.get('filename')
                progress.pack_forget()
                progress.set(0)

        ydl_opts = {
            'quiet': True,
            'format': f'{format_id}+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_name + '.%(ext)s',
            'merge_output_format': 'mp4',
            'ffmpeg_location': 'C:/ffmpeg/bin/ffmpeg.exe',
            'progress_hooks': [progress_hook],
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # หาไฟล์ที่น่าจะเป็นผลลัพธ์สุดท้าย
            merged_file = None
            for ext in ['mp4', 'mkv', 'webm']:
                candidate = f"{output_name}.{ext}"
                if os.path.exists(candidate):
                    merged_file = candidate
                    break

            if merged_file:
                merging[0] = False  # หยุดการแอนิเมชัน
                result_label.configure(text="รวมไฟล์เสร็จ ✅")
                save_as(merged_file)
            else:
                result_label.configure(text="ไม่พบไฟล์ที่รวมแล้ว ❌")

        except Exception as e:
            if "[Errno 28] No space left on device" in str(e):
                result_label.configure(text="⚠️ พื้นที่เก็บข้อมูลไม่เพียงพอ")
            else:
                result_label.configure(text=f"❌ เกิดข้อผิดพลาดในการดาวน์โหลด: {e}")

    threading.Thread(target=run).start()

progress = ctk.CTkProgressBar(right_frame)
progress.set(0)
progress.configure(mode="determinate")
progress.pack_forget()  # ซ่อนไว้ก่อน

app.mainloop()