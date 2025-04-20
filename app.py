import customtkinter as ctk
from PIL import Image
from yt_dlp import YoutubeDL
import requests
import io
import threading

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
url_entry = ctk.CTkEntry(right_frame, placeholder_text="วาง URL ที่นี่")
url_entry.pack(pady=(20, 10), padx=10, fill="x")
last_url = [None]  # ใช้ list เพื่อให้แก้ได้ภายใน nested function

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

download_btn = ctk.CTkButton(right_frame, text="ดาวน์โหลด", command=lambda: download_format())
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
                result_label.configure(text="ดึงข้อมูลไม่สำเร็จ")
                return

            # แสดงข้อมูลด้านซ้าย
            title_label.configure(text=info.get("title", ""))
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

                # Video
                if f.get('vcodec') != 'none' and f.get('height'):
                    key = (f.get('height'), ext)
                    if key not in best_video or parse_format_id(best_video[key]['format_id']) < fid_num:
                        best_video[key] = f
                # Audio
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

# ⬇️ ดาวน์โหลด
def download_format():
    url = url_entry.get()
    selected = dropdown.get()
    if not url or selected not in format_dict:
        result_label.configure(text="กรุณาเลือกตัวเลือกให้ถูกต้อง")
        return

    format_id = format_dict[selected]
    result_label.configure(text="กำลังดาวน์โหลด...")

    def run():
        ydl_opts = {
            'quiet': False,
            'format': format_id,
            'outtmpl': '%(title)s.%(ext)s',
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            result_label.configure(text="ดาวน์โหลดเสร็จแล้ว ✅")
        except Exception as e:
            result_label.configure(text="เกิดข้อผิดพลาดระหว่างดาวน์โหลด ❌")

    threading.Thread(target=run).start()

app.mainloop()