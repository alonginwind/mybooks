import argparse
from pathlib import Path
from PIL import Image


def get_white_border_thickness(img, tolerance=200):
    """
    计算图像四周符合纯白（R, G, B 均大于等于 tolerance）的白边厚度。
    """
    width, height = img.size
    pixels = img.load()

    # 检查单像素是否属于符合条件的白色
    def is_white(p):
        if isinstance(p, tuple):
            return p[0] >= tolerance and p[1] >= tolerance and p[2] >= tolerance
        return p >= tolerance  # 灰度图情况

    # 1. 检测顶部白边厚度
    top = 0
    for y in range(height):
        if all(is_white(pixels[x, y]) for x in range(width)):
            top += 1
        else:
            break

    # 2. 检测底部白边厚度
    bottom = 0
    for y in range(height - 1, -1, -1):
        if all(is_white(pixels[x, y]) for x in range(width)):
            bottom += 1
        else:
            break

    # 3. 检测左侧白边厚度
    left = 0
    for x in range(width):
        if all(is_white(pixels[x, y]) for y in range(height)):
            left += 1
        else:
            break

    # 4. 检测右侧白边厚度
    right = 0
    for x in range(width - 1, -1, -1):
        if all(is_white(pixels[x, y]) for y in range(height)):
            right += 1
        else:
            break

    return left, top, right, bottom


def crop_symmetric_white_borders(
    image_path, output_path, color_threshold=200, symmetry_error=3, margin=0
):
    """
    根据对称性裁剪白边
    :param image_path: 输入图片路径
    :param output_path: 输出图片路径
    :param color_threshold: 判定为白色的阈值（默认200以上）
    :param symmetry_error: 对称判定的误差范围（像素单位）
    :param margin: 需要保留的边缘大小（默认0像素）
    """
    # 打开图片并转为 RGB 模式
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    # 获取四周的白边厚度
    left, top, right, bottom = get_white_border_thickness(img, color_threshold)

    # 初始化最终裁剪边界为原图边界
    crop_left, crop_top, crop_right, crop_bottom = 0, 0, width, height
    need_crop = False

    # 检测左右对称性：必须两边都有白边，且厚度差在误差范围内
    if left > 0 and right > 0 and abs(left - right) <= symmetry_error:
        actual_crop_left = max(0, left - margin)
        actual_crop_right = max(0, right - margin)

        if actual_crop_left > 0 or actual_crop_right > 0:
            crop_left = actual_crop_left
            crop_right = width - actual_crop_right
            need_crop = True
            print(
                f"检测到左右对称白边: 左 {left}px, 右 {right}px。保留 {margin}px 边缘进行左右裁剪。"
            )

    # 检测上下对称性：必须两边都有白边，且厚度差在误差范围内
    if top > 0 and bottom > 0 and abs(top - bottom) <= symmetry_error:
        actual_crop_top = max(0, top - margin)
        actual_crop_bottom = max(0, bottom - margin)

        if actual_crop_top > 0 or actual_crop_bottom > 0:
            crop_top = actual_crop_top
            crop_bottom = height - actual_crop_bottom
            need_crop = True
            print(
                f"检测到上下对称白边: 上 {top}px, 下 {bottom}px。保留 {margin}px 边缘进行上下裁剪。"
            )

    # 执行裁剪与保存
    if need_crop:
        # crop 接收元组: (左, 上, 右, 下)
        cropped_img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        cropped_img.save(output_path)
        print(f"处理完成，新尺寸为: {cropped_img.size}")
    else:
        # 不满足对称条件，不作处理，保留原图
        img.save(output_path)
        print("未检测到符合对称条件的白边，跳过裁剪，已保留原样。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据对称性裁剪图片白边")
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        required=True,
        help="要处理的封面路径（单个文件或目录）",
    )
    parser.add_argument(
        "-o", "--output", dest="output_dir", required=True, help="输出目录"
    )
    parser.add_argument(
        "-m", "--margin", type=int, default=0, help="需要保留的边缘大小（默认0像素）"
    )
    parser.add_argument(
        "--threshold", type=int, default=200, help="判定为白色的阈值（默认200）"
    )
    parser.add_argument(
        "--error", type=int, default=3, help="对称判定的误差范围（默认3像素）"
    )

    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)

    # 如果输出目录不存在，自动创建
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        output_file = output_dir / input_path.name
        print(f"处理: {input_path.name}")
        crop_symmetric_white_borders(
            str(input_path),
            str(output_file),
            color_threshold=args.threshold,
            symmetry_error=args.error,
            margin=args.margin,
        )
    elif input_path.is_dir():
        for file_path in input_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
            ]:
                output_file = output_dir / file_path.name
                print(f"处理: {file_path.name}")
                try:
                    crop_symmetric_white_borders(
                        str(file_path),
                        str(output_file),
                        color_threshold=args.threshold,
                        symmetry_error=args.error,
                        margin=args.margin,
                    )
                except Exception as e:
                    print(f"处理 {file_path.name} 时出错: {e}")
    else:
        print(f"输入路径无效或不存在: {input_path}")
