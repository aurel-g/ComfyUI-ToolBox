import os
import base64
import io
from PIL import Image
import folder_paths
import numpy as np
import torch

class OpenAISaveImageNode:
    """保存 OpenAI 返回的图像数据到文件"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "b64_json": ("STRING", {"default": "", "multiline": True, "placeholder": "OpenAI API 返回的 base64 编码图像数据"}),
                "filename_prefix": ("STRING", {"default": "openai"}),
            }
        }

    RETURN_TYPES = ("STRING", "IMAGE",)
    RETURN_NAMES = ("filename", "image",)
    FUNCTION = "save_image"
    CATEGORY = "ToolBox/OpenAI"

    def save_image(self, b64_json, filename_prefix):
        print(f"接收到 base64 数据，长度: {len(b64_json)}")
        
        try:
            # 解码 base64 数据
            image_data = base64.b64decode(b64_json)
            print(f"解码后的图像数据大小: {len(image_data)} 字节")
            
            # 使用 PIL 打开图像
            image = Image.open(io.BytesIO(image_data))
            print(f"解码图像成功，尺寸: {image.size}, 模式: {image.mode}")
            
            # 确保图像处于 RGB 模式
            if image.mode != 'RGB':
                print(f"转换图像从 {image.mode} 到 RGB 模式")
                image = image.convert('RGB')
                
            # 获取输出目录
            output_dir = folder_paths.get_output_directory()
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            counter = 1
            while True:
                filename = f"{filename_prefix}_{counter:05d}.png"
                filepath = os.path.join(output_dir, filename)
                if not os.path.exists(filepath):
                    break
                counter += 1
                
            # 保存图像
            print(f"保存图像到: {filepath}")
            image.save(filepath)
            
            # 转换为 numpy 数组
            img_np = np.array(image).astype(np.float32) / 255.0
            
            # 转换为 PyTorch 张量 (CHW 格式) - ComfyUI 期望的格式是 [batch, channels, height, width]
            tensor = torch.from_numpy(img_np).permute(2, 0, 1).unsqueeze(0)
            print(f"创建张量形状: {tensor.shape}")
            
            # 确保返回的是 [batch, channels, height, width] 格式
            if tensor.shape[0] != 1 or tensor.shape[1] != 3:
                print(f"警告: 张量形状 {tensor.shape} 不符合要求，进行调整")
                if tensor.dim() == 3:  # [C,H,W]
                    tensor = tensor.unsqueeze(0)  # 添加批次维度
                elif tensor.dim() == 4 and tensor.shape[1] != 3:
                    # 如果是 [1,1,H,W] 或其他不合规格式，调整为 [1,3,H,W]
                    tensor = tensor.repeat(1, 3, 1, 1) if tensor.shape[1] == 1 else tensor[:,:3]
            
            print(f"最终输出张量形状: {tensor.shape}")
            return (filepath, tensor)
            
        except Exception as e:
            print(f"图像保存失败: {str(e)}")
            # 创建一个空的 1x3x64x64 张量作为备用
            empty_tensor = torch.zeros((1, 3, 64, 64), dtype=torch.float32)
            return (f"error: {str(e)}", empty_tensor) 