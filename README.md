# Video-Image-Photo-Converter

## 功能特性
- **图片处理**：
  - 支持 JPG、PNG、BMP、TIFF、RAW 等格式互转。
  - 支持批量图片转换和简单调整。
- **视频处理**：
  - 支持 MP4、AVI、MKV、MOV 等多种视频格式互转。
  - 支持从视频中提取音频，分离音轨和视频轨道。
- **音频处理**：
  - 支持 MP3、WAV、AAC、FLAC 等格式互转。
  - 支持音频质量调整，如比特率转换和降噪处理。
--

## 使用方法

### 环境准备
1. **安装 ffmpeg**  
   请先下载并安装 [FFmpeg](https://ffmpeg.org/download.html)。

2. **克隆仓库**  
   使用以下命令将仓库克隆到本地：
   ```bash
   https://github.com/Vrepol/Video-image-photo-converter-.git
   ```
   
3.**安装依赖**
  确保已安装 Python 3.x，然后运行以下命令安装项目依赖：
    ```
    pip install -r requirements.txt
    ```
   
4.**运行**
  运行以下命令启动 GUI 界面：
    ```
    python gui_converter.py
    ```


#### 4. **界面截图**
- 界面截图的展示方式可以改为清晰的分步图解，并添加描述：
```markdown
**界面示例：**

1. 主界面：
   - 支持拖拽文件进行转换操作。
   - 提供多种格式选项。
   
   ![主界面](img/1.png)

2. 视频处理页面：
   - 可以选择提取音频、分离视频轨道。
   
   ![视频处理页面](img/2.png)

3. 音频处理页面：
   - 支持调整音频比特率和采样率。
   
   ![音频处理页面](img/3.png)

