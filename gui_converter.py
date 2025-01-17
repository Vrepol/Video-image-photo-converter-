import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import rawpy
import imageio
from moviepy import VideoFileClip, AudioFileClip
import subprocess
import platform
from threading import Thread
import logging

# 日志配置
logging.basicConfig(filename='media_converter.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ------------------ 转换/操作函数 ------------------ #

def convert_image(input_file_path, output_format='jpeg', output_dir=None):
    """
    将各类图片/RAW 文件转换为指定格式。
    """
    try:
        filename = os.path.basename(input_file_path)
        name_wo_ext, ext = os.path.splitext(filename)
        # 判断是否是 RAW
        if ext.lower() in ['.cr2', '.nef', '.arw', '.raw', '.raf', '.rw2', '.orf', '.dng']:
            with rawpy.imread(input_file_path) as raw:
                rgb = raw.postprocess()
        else:
            rgb = imageio.imread(input_file_path)

        # 输出路径
        output_path = (os.path.join(output_dir, f"{name_wo_ext}.{output_format}")
                       if output_dir else f"{os.path.splitext(input_file_path)[0]}.{output_format}")
        imageio.imsave(output_path, rgb)
        logging.info(f"图片转换成功: {input_file_path} -> {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"图片转换失败: {input_file_path}, 错误: {e}")
        messagebox.showerror("错误", f"图片转换失败：{e}")
        return None

def separate_audio_from_video(video_path, output_dir=None, export_only_audio=False,
                              audio_format='mp3', video_format='mp4'):
    """
    使用 moviepy 分离音频。
      - export_only_audio = True 则不输出“无声视频”。
      - audio_format / video_format 分别指定音频和视频封装格式（如 mp3、wav，mp4、mov 等）
    注意：如果要“保持原视频编码”，可以改用 ffmpeg 命令行完成拷贝模式(-c copy)。
    """
    try:
        clip = VideoFileClip(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        audio_out = (os.path.join(output_dir, f"{base_name}_extracted_audio.{audio_format}")
                     if output_dir else f"{os.path.splitext(video_path)[0]}_extracted_audio.{audio_format}")
        video_out = (os.path.join(output_dir, f"{base_name}_no_audio.{video_format}")
                     if output_dir else f"{os.path.splitext(video_path)[0]}_no_audio.{video_format}")

        if clip.audio:
            # 导出音频
            if audio_format.lower() == 'wav':
                clip.audio.write_audiofile(audio_out, codec="pcm_s16le")
            else:
                clip.audio.write_audiofile(audio_out, codec=audio_format.lower())

        else:
            audio_out = "无音频"

        # 如仅要音频，则不输出无声视频
        if not export_only_audio:
            clip_no_audio = clip.without_audio()
            clip_no_audio.write_videofile(video_out, codec="libx264", audio=False)
            clip_no_audio.close()

        clip.close()
        logging.info(f"分离音频成功: {video_path} -> {audio_out}, {video_out}")
        return video_out if not export_only_audio else None, audio_out
    except Exception as e:
        logging.error(f"分离音频失败: {video_path}, 错误: {e}")
        messagebox.showerror("错误", f"分离音频失败：{e}")
        return None, None

def convert_audio_format(audio_path, output_format='mp3', output_dir=None):
    """
    使用 moviepy 对音频重新编码，例如转mp3、wav等。
    """
    try:
        audio = AudioFileClip(audio_path)
        name_wo_ext = os.path.splitext(os.path.basename(audio_path))[0]
        output_file = (os.path.join(output_dir, f"{name_wo_ext}.{output_format}")
                       if output_dir else f"{os.path.splitext(audio_path)[0]}.{output_format}")

        # 根据目标格式，确定编码器
        codec = 'pcm_s16le' if output_format.lower() == 'wav' else output_format.lower()
        audio.write_audiofile(output_file, codec=codec)
        audio.close()
        logging.info(f"音频转换成功: {audio_path} -> {output_file}")
        return output_file
    except Exception as e:
        logging.error(f"音频转换失败: {audio_path}, 错误: {e}")
        messagebox.showerror("错误", f"音频转换失败：{e}")
        return None

def open_path(path, open_folder=False):
    """
    打开指定文件或文件夹。
    """
    try:
        system = platform.system()
        if open_folder:
            folder = os.path.dirname(path) if os.path.isfile(path) else path
            if system == 'Windows':
                os.startfile(folder)
            elif system == 'Darwin':
                subprocess.call(['open', folder])
            else:
                subprocess.call(['xdg-open', folder])
        else:
            if system == 'Windows':
                os.startfile(path)
            elif system == 'Darwin':
                subprocess.call(['open', path])
            else:
                subprocess.call(['xdg-open', path])
    except Exception as e:
        messagebox.showerror("错误", f"无法打开路径：{e}")

# ------------------ 主界面 ------------------ #

class MediaConverterApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("多媒体转换工具")
        self.geometry("900x800")
        self.configure(bg="#f0f0f0")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # 初始化各个标签页
        self.image_tab = ttk.Frame(self.notebook)
        self.video_tab = ttk.Frame(self.notebook)
        self.audio_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.image_tab, text='图片转换')
        self.notebook.add(self.video_tab, text='视频转换')
        self.notebook.add(self.audio_tab, text='音频转换')

        # 用于存放不同分类的文件
        self.image_files = []
        self.video_files = []
        self.audio_files = []

        # 输出目录（分别记录）
        self.image_specify_dir = ""
        self.video_specify_dir = ""
        self.audio_specify_dir = ""

        # 创建三个选项卡的界面
        self.create_image_tab()
        self.create_video_tab()
        self.create_audio_tab()

    # ------------------ 通用小工具函数 ------------------ #
    def toggle_dir_button(self, var, button):
        """当 var 为 'specify' 时启用按钮，否则禁用。"""
        button.config(state='normal' if var.get() == 'specify' else 'disabled')

    def split_filenames(self, data):
        """解析拖放的文件路径，兼容 Windows 和非 Windows。"""
        return self.tk.splitlist(data) if self.tk.call('tk', 'windowingsystem') == 'win32' else data.split()

    def choose_output_dir(self, tab_type):
        """选择输出目录。"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            if tab_type == 'image':
                self.image_specify_dir = directory
            elif tab_type == 'video':
                self.video_specify_dir = directory
            elif tab_type == 'audio':
                self.audio_specify_dir = directory

    def add_files(self, filetypes, store_list, listbox):
        """通用的添加文件函数。"""
        files = filedialog.askopenfilenames(title="选择文件", filetypes=filetypes)
        for f in files:
            if f not in store_list:
                store_list.append(f)
                listbox.insert(tk.END, f)

    def drop_files(self, event, store_list, listbox, supported_exts):
        """通用的拖放文件函数。"""
        for f in self.split_filenames(event.data):
            if os.path.isfile(f) and f not in store_list:
                if os.path.splitext(f)[1].lower() in supported_exts:
                    store_list.append(f)
                    listbox.insert(tk.END, f)
                else:
                    messagebox.showwarning("警告", f"不支持的文件类型：{f}")

    def clear_files(self, store_list, listbox):
        store_list.clear()
        listbox.delete(0, tk.END)

    def open_selected_file(self, tree, is_folder=False):
        """从 TreeView 里打开文件或所在文件夹。"""
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("信息", "请选择一个转换结果。")
            return
        item = tree.item(sel[0])  # 只处理第一个被选中的
        outputs = str(item['values'][1]).split('\n')
        for out in outputs:
            if out != "无音频" and os.path.exists(out):
                open_path(out, open_folder=is_folder)
            else:
                messagebox.showwarning("警告", f"输出文件不存在或无效：{out}")

    # ------------------ 图片选项卡 ------------------ #
    def create_image_tab(self):
        frame = ttk.Frame(self.image_tab, padding=10)
        frame.pack(fill='both', expand=True)

        # 1) 文件选择
        file_frame = ttk.LabelFrame(frame, text="选择图片文件")
        file_frame.pack(fill='x', pady=5)
        self.image_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, height=5)
        self.image_listbox.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.image_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.image_listbox.config(yscrollcommand=scrollbar.set)

        btns_frame = ttk.Frame(frame)
        btns_frame.pack(fill='x', pady=5)
        ttk.Button(btns_frame, text="添加文件",
                   command=lambda: self.add_files(
                       [("图片文件", "*.CR2 *.NEF *.ARW *.RAW *.RAF *.RW2 *.ORF *.DNG *.JPEG *.JPG *.PNG *.TIFF *.BMP *.GIF *.WEBP"),
                        ("所有文件", "*.*")],
                       self.image_files,
                       self.image_listbox)
                   ).pack(side='left', padx=5)
        ttk.Button(btns_frame, text="清除文件",
                   command=lambda: self.clear_files(self.image_files, self.image_listbox)
                   ).pack(side='left', padx=5)

        # 拖放
        self.image_listbox.drop_target_register(DND_FILES)
        self.image_listbox.dnd_bind('<<Drop>>',
            lambda e: self.drop_files(e, self.image_files, self.image_listbox,
                                      ['.cr2','.nef','.arw','.raw','.raf','.rw2','.orf','.dng',
                                       '.jpeg','.jpg','.png','.tiff','.bmp','.gif','.webp']))

        # 2) 输出格式
        fmt_frame = ttk.LabelFrame(frame, text="输出格式")
        fmt_frame.pack(fill='x', pady=5)
        self.output_format = tk.StringVar(value="jpeg")
        ttk.Label(fmt_frame, text="选择格式:").pack(side='left', padx=5)
        self.format_combobox = ttk.Combobox(fmt_frame, textvariable=self.output_format, state='readonly',
                                            values=("jpeg", "png", "tiff", "bmp", "gif", "webp"))
        self.format_combobox.pack(side='left', padx=5)
        self.format_combobox.current(0)

        # 3) 输出目录
        out_dir_frame = ttk.LabelFrame(frame, text="输出目录")
        out_dir_frame.pack(fill='x', pady=5)
        self.image_output_dir_option = tk.StringVar(value="same")
        for val, txt in [("same", "与原文件相同"), ("specify", "指定目录")]:
            ttk.Radiobutton(out_dir_frame, text=txt, variable=self.image_output_dir_option, value=val).pack(side='left', padx=5)
        btn_dir = ttk.Button(out_dir_frame, text="选择目录", command=lambda: self.choose_output_dir('image'))
        btn_dir.pack(side='left', padx=5)
        btn_dir.config(state='disabled')
        self.image_output_dir_option.trace('w',
            lambda *args: self.toggle_dir_button(self.image_output_dir_option, btn_dir))

        # 4) 转换 & 进度
        ttk.Button(frame, text="开始转换", command=self.start_convert_images).pack(pady=10)
        self.image_progress = ttk.Progressbar(frame, orient='horizontal', mode='determinate')
        self.image_progress.pack(fill='x', padx=5, pady=5)

        # 5) 结果列表
        result_frame = ttk.LabelFrame(frame, text="转换结果")
        result_frame.pack(fill='both', expand=True, pady=5)
        self.image_results = ttk.Treeview(result_frame, columns=("原文件", "输出文件"), show='headings')
        for col in ("原文件", "输出文件"):
            self.image_results.heading(col, text=col)
        self.image_results.pack(fill='both', expand=True, padx=5, pady=5)

        # 6) 打开文件/文件夹
        open_btns = ttk.Frame(frame)
        open_btns.pack(pady=5)
        ttk.Button(open_btns, text="打开文件",
                   command=lambda: self.open_selected_file(self.image_results, is_folder=False)
                   ).pack(side='left', padx=5)
        ttk.Button(open_btns, text="打开所在文件夹",
                   command=lambda: self.open_selected_file(self.image_results, is_folder=True)
                   ).pack(side='left', padx=5)

    def start_convert_images(self):
        if not self.image_files:
            messagebox.showinfo("信息", "请先添加图片文件。")
            return
        for i in self.image_results.get_children():
            self.image_results.delete(i)
        Thread(target=self.convert_images_thread, daemon=True).start()

    def convert_images_thread(self):
        total = len(self.image_files)
        self.image_progress['maximum'] = total
        out_fmt = self.output_format.get()
        out_dir = self.image_specify_dir if self.image_output_dir_option.get() == "specify" else None

        for idx, f in enumerate(self.image_files, start=1):
            res = convert_image(f, out_fmt, out_dir)
            if res:
                self.image_results.insert("", "end", values=(f, res))
            self.image_progress['value'] = idx
            self.update_idletasks()

        messagebox.showinfo("完成", "图片转换完成。")

    # ------------------ 视频选项卡 ------------------ #
    def create_video_tab(self):
        frame = ttk.Frame(self.video_tab, padding=10)
        frame.pack(fill='both', expand=True)

        # 1) 文件选择
        file_frame = ttk.LabelFrame(frame, text="选择视频文件")
        file_frame.pack(fill='x', pady=5)
        self.video_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, height=5)
        self.video_listbox.pack(side='left', fill='both', expand=True, padx=(5,0), pady=5)
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.video_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.video_listbox.config(yscrollcommand=scrollbar.set)

        btns_frame = ttk.Frame(frame)
        btns_frame.pack(fill='x', pady=5)
        ttk.Button(btns_frame, text="添加文件",
                   command=lambda: self.add_files(
                       [("视频文件", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv"),
                        ("所有文件", "*.*")],
                       self.video_files,
                       self.video_listbox)
                   ).pack(side='left', padx=5)
        ttk.Button(btns_frame, text="清除文件",
                   command=lambda: self.clear_files(self.video_files, self.video_listbox)
                   ).pack(side='left', padx=5)

        self.video_listbox.drop_target_register(DND_FILES)
        self.video_listbox.dnd_bind('<<Drop>>',
            lambda e: self.drop_files(e, self.video_files, self.video_listbox,
                                      ['.mp4','.mov','.avi','.mkv','.flv','.wmv']))

        # 2) 输出目录
        out_dir_frame = ttk.LabelFrame(frame, text="输出目录")
        out_dir_frame.pack(fill='x', pady=5)
        self.video_output_dir_option = tk.StringVar(value="same")
        for val, txt in [("same", "与原文件相同"), ("specify", "指定目录")]:
            ttk.Radiobutton(out_dir_frame, text=txt, variable=self.video_output_dir_option, value=val).pack(side='left', padx=5)
        btn_dir = ttk.Button(out_dir_frame, text="选择目录", command=lambda: self.choose_output_dir('video'))
        btn_dir.pack(side='left', padx=5)
        btn_dir.config(state='disabled')
        self.video_output_dir_option.trace('w',
            lambda *args: self.toggle_dir_button(self.video_output_dir_option, btn_dir))

        # 3) 仅导出音频(可选) + 音频格式
        self.audio_only_var = tk.BooleanVar(value=False)
        chk_frame = ttk.Frame(frame)
        chk_frame.pack(fill='x', pady=5)
        ttk.Checkbutton(chk_frame, text="仅导出音频", variable=self.audio_only_var).pack(side='left', padx=5)

        audio_fmt_frame = ttk.LabelFrame(frame, text="选择音频输出格式")
        audio_fmt_frame.pack(fill='x', pady=5)
        self.video_audio_format = tk.StringVar(value="mp3")
        ttk.Label(audio_fmt_frame, text="音频格式:").pack(side='left', padx=5)
        cb_audio = ttk.Combobox(audio_fmt_frame, textvariable=self.video_audio_format,
                                values=["mp3","wav","aac","flac","ogg","m4a"], state='readonly')
        cb_audio.pack(side='left', padx=5)
        cb_audio.current(0)

        # ★ 如果不需要改视频格式，可以把下面这些删除或注释。
        # 这里先演示“保留原视频扩展名”做无声视频输出。
        """
        video_fmt_frame = ttk.LabelFrame(frame, text="输出视频格式")
        video_fmt_frame.pack(fill='x', pady=5)
        self.video_video_format = tk.StringVar(value="mp4")
        ttk.Label(video_fmt_frame, text="视频格式:").pack(side='left', padx=5)
        cb_video = ttk.Combobox(video_fmt_frame, textvariable=self.video_video_format,
                                values=["mp4","mov","avi","mkv","flv","wmv"], state='readonly')
        cb_video.pack(side='left', padx=5)
        cb_video.current(0)
        """

        # 4) 转换按钮 & 进度
        ttk.Button(frame, text="开始转换", command=self.start_convert_videos).pack(pady=10)
        self.video_progress = ttk.Progressbar(frame, orient='horizontal', mode='determinate')
        self.video_progress.pack(fill='x', padx=5, pady=5)

        # 5) 结果
        result_frame = ttk.LabelFrame(frame, text="转换结果")
        result_frame.pack(fill='both', expand=True, pady=5)
        self.video_results = ttk.Treeview(result_frame, columns=("原文件", "输出文件"), show='headings')
        for col in ("原文件", "输出文件"):
            self.video_results.heading(col, text=col)
        self.video_results.pack(fill='both', expand=True, padx=5, pady=5)

        open_btns = ttk.Frame(frame)
        open_btns.pack(pady=5)
        ttk.Button(open_btns, text="打开文件",
                   command=lambda: self.open_selected_file(self.video_results, is_folder=False)
                   ).pack(side='left', padx=5)
        ttk.Button(open_btns, text="打开所在文件夹",
                   command=lambda: self.open_selected_file(self.video_results, is_folder=True)
                   ).pack(side='left', padx=5)

    def start_convert_videos(self):
        """开始转换（或提取）音频"""
        if not self.video_files:
            messagebox.showinfo("信息", "请先添加视频文件。")
            return
        # 清空旧结果
        for i in self.video_results.get_children():
            self.video_results.delete(i)
        Thread(target=self.convert_videos_thread, daemon=True).start()

    def convert_videos_thread(self):
        total = len(self.video_files)
        self.video_progress['maximum'] = total
        out_dir = self.video_specify_dir if self.video_output_dir_option.get() == "specify" else None

        audio_fmt = self.video_audio_format.get()   # 用户在下拉框里选的音频格式
        only_audio = self.audio_only_var.get()

        for idx, f in enumerate(self.video_files, start=1):
            try:
                # 先提取音频：这里为了更灵活，统一先提取成 wav，再用 convert_audio_format() 转目标格式
                original_ext = os.path.splitext(f)[1]  # e.g. ".mp4"
                v_out, a_out = separate_audio_from_video(
                    video_path       = f,
                    output_dir       = out_dir,
                    export_only_audio= only_audio,
                    audio_format     = "wav",   # 先提取成 wav
                    video_format     = original_ext.lstrip('.')  # 保留原视频后缀
                )

                # 如果分离出了音频，且不是“无音频”，再调用音频转换函数
                final_audio_path = None
                if a_out and a_out != "无音频":
                    final_audio_path = convert_audio_format(a_out, output_format=audio_fmt, output_dir=out_dir)

                # 将结果插入 Treeview
                if only_audio:
                    # 仅要音频
                    if final_audio_path:
                        self.video_results.insert("", "end", values=(f, final_audio_path))
                    else:
                        self.video_results.insert("", "end", values=(f, "无音频轨"))
                else:
                    # 分离音频 + 无声视频
                    if v_out and final_audio_path:
                        self.video_results.insert("", "end",
                                                  values=(f, f"{v_out}\n{final_audio_path}"))
                    elif v_out:
                        self.video_results.insert("", "end", values=(f, v_out))
                    elif final_audio_path:
                        self.video_results.insert("", "end", values=(f, final_audio_path))
                    else:
                        self.video_results.insert("", "end", values=(f, "无音频且无输出文件"))

            except Exception as e:
                logging.error(f"处理视频出错: {f}, 错误: {e}")
                self.video_results.insert("", "end", values=(f, f"出错：{e}"))

            self.video_progress['value'] = idx
            self.update_idletasks()

        messagebox.showinfo("完成", "视频处理完成。")

    # ------------------ 音频选项卡 ------------------ #
    def create_audio_tab(self):
        frame = ttk.Frame(self.audio_tab, padding=10)
        frame.pack(fill='both', expand=True)

        file_frame = ttk.LabelFrame(frame, text="选择音频文件")
        file_frame.pack(fill='x', pady=5)
        self.audio_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, height=5)
        self.audio_listbox.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.audio_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.audio_listbox.config(yscrollcommand=scrollbar.set)

        btns_frame = ttk.Frame(frame)
        btns_frame.pack(fill='x', pady=5)
        ttk.Button(btns_frame, text="添加文件",
                   command=lambda: self.add_files(
                       [("音频文件", "*.mp3 *.wav *.aac *.flac *.ogg *.m4a"),
                        ("所有文件","*.*")],
                       self.audio_files,
                       self.audio_listbox)
                   ).pack(side='left', padx=5)
        ttk.Button(btns_frame, text="清除文件",
                   command=lambda: self.clear_files(self.audio_files, self.audio_listbox)
                   ).pack(side='left', padx=5)

        self.audio_listbox.drop_target_register(DND_FILES)
        self.audio_listbox.dnd_bind('<<Drop>>',
            lambda e: self.drop_files(e, self.audio_files, self.audio_listbox,
                                      ['.mp3','.wav','.aac','.flac','.ogg','.m4a']))

        fmt_frame = ttk.LabelFrame(frame, text="输出格式")
        fmt_frame.pack(fill='x', pady=5)
        self.audio_output_format = tk.StringVar(value="mp3")
        ttk.Label(fmt_frame, text="选择格式:").pack(side='left', padx=5)
        cb = ttk.Combobox(fmt_frame, textvariable=self.audio_output_format, state='readonly',
                          values=["mp3","wav","aac","flac","ogg","m4a"])
        cb.pack(side='left', padx=5)
        cb.current(0)

        out_dir_frame = ttk.LabelFrame(frame, text="输出目录")
        out_dir_frame.pack(fill='x', pady=5)
        self.audio_output_dir_option = tk.StringVar(value="same")
        for val, txt in [("same", "与原文件相同"), ("specify", "指定目录")]:
            ttk.Radiobutton(out_dir_frame, text=txt, variable=self.audio_output_dir_option, value=val).pack(side='left', padx=5)
        btn_dir = ttk.Button(out_dir_frame, text="选择目录", command=lambda: self.choose_output_dir('audio'))
        btn_dir.pack(side='left', padx=5)
        btn_dir.config(state='disabled')
        self.audio_output_dir_option.trace('w',
            lambda *args: self.toggle_dir_button(self.audio_output_dir_option, btn_dir))

        ttk.Button(frame, text="开始转换", command=self.start_convert_audios).pack(pady=10)
        self.audio_progress = ttk.Progressbar(frame, orient='horizontal', mode='determinate')
        self.audio_progress.pack(fill='x', padx=5, pady=5)

        result_frame = ttk.LabelFrame(frame, text="转换结果")
        result_frame.pack(fill='both', expand=True, pady=5)
        self.audio_results = ttk.Treeview(result_frame, columns=("原文件", "输出文件"), show='headings')
        for col in ("原文件", "输出文件"):
            self.audio_results.heading(col, text=col)
        self.audio_results.pack(fill='both', expand=True, padx=5, pady=5)

        open_btns = ttk.Frame(frame)
        open_btns.pack(pady=5)
        ttk.Button(open_btns, text="打开文件",
                   command=lambda: self.open_selected_file(self.audio_results, is_folder=False)
                   ).pack(side='left', padx=5)
        ttk.Button(open_btns, text="打开所在文件夹",
                   command=lambda: self.open_selected_file(self.audio_results, is_folder=True)
                   ).pack(side='left', padx=5)

    def start_convert_audios(self):
        if not self.audio_files:
            messagebox.showinfo("信息", "请先添加音频文件。")
            return
        for i in self.audio_results.get_children():
            self.audio_results.delete(i)
        Thread(target=self.convert_audios_thread, daemon=True).start()

    def convert_audios_thread(self):
        total = len(self.audio_files)
        self.audio_progress['maximum'] = total
        out_fmt = self.audio_output_format.get()
        out_dir = self.audio_specify_dir if self.audio_output_dir_option.get() == "specify" else None

        for idx, f in enumerate(self.audio_files, start=1):
            res = convert_audio_format(f, out_fmt, out_dir)
            if res:
                self.audio_results.insert("", "end", values=(f, res))
            self.audio_progress['value'] = idx
            self.update_idletasks()

        messagebox.showinfo("完成", "音频转换完成。")

def main():
    app = MediaConverterApp()
    app.mainloop()

if __name__ == "__main__":
    main()
