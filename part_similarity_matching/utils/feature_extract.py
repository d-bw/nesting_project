import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cv2
import argparse
from transformers import pipeline
import torch
from sklearn.metrics.pairwise import cosine_similarity


def preprocess_img_byCanny(raw_image):
    #raw_image = cv2.imread(raw_image)
    image = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
    # 将图像转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 边缘检测
    edges = cv2.Canny(gray, 50, 150)

    # 查找轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # # 遍历每个轮廓并绘制矩形框
    # for contour in contours:
    #     x, y, w, h = cv2.boundingRect(contour)
    #     cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # 计算每个轮廓的bounding box并计算面积
    bounding_boxes = [cv2.boundingRect(contour) for contour in contours]
    bounding_boxes_areas = [w * h for x, y, w, h in bounding_boxes]

    # 按照bounding box面积对轮廓进行排序
    sorted_indices = np.argsort(bounding_boxes_areas)[::-1]

    # 框出面积最大的bounding box
    if len(sorted_indices) > 0:
        largest_box_index = sorted_indices[0]
        x, y, w, h = bounding_boxes[largest_box_index]
        # cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # 额外预留30个单位的误差
        x -= 15
        y -= 15
        w += 30
        h += 30

        # 裁剪图像
        cropped_img = raw_image[max(y, 0):min(y + h, raw_image.shape[0]), max(x, 0):min(x + w, raw_image.shape[1])]
        cropped_pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
        return cropped_pil_img
    else:
        return raw_image


def preprocess_img_byRmBackground(raw_image):
    #image = cv2.imread(raw_image)

    image = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
    # 将图像转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 使用大津法确定阈值
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 查找轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 创建一个与原始图像相同大小的掩码
    mask = np.zeros_like(image)

    # 绘制轮廓到掩码上
    cv2.drawContours(mask, contours, -1, (255, 255, 255), thickness=cv2.FILLED)

    # 使用掩码提取零件
    result = np.bitwise_and(image, mask)

    bounding_boxes = []
    # 在原图上绘制边界框
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        bounding_boxes.append(((x, y), (x + w, y + h)))
        # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    bounding_boxes.sort(key=lambda box: (box[1][0] - box[0][0]) * (box[1][1] - box[0][1]), reverse=True)
    if len(bounding_boxes) > 0:
        # 绘制面积最大的边界框到原图上
        x1, y1 = bounding_boxes[0][0]
        x2, y2 = bounding_boxes[0][1]
        # 增加10个单位容错区间
        x1 -= 10
        y1 -= 10
        x2 += 10
        y2 += 10
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cropped_image = image[y1:y2, x1:x2]
        # 显示结果
        # cv2_imshow(image)
        cropped_pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
        return cropped_pil_image
    else:
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


# 提取主要物体mask
def extract_main_object_mask(masks):
    # 计算每个mask的面积，并将其与对应的mask一起存储在一个列表中
    masks_with_areas = [(mask, np.sum(mask)) for mask in masks]

    # 使用面积作为关键字进行排序
    sorted_masks = sorted(masks_with_areas, key=lambda x: x[1], reverse=True)

    # 仅返回排序后的masks，不包括面积信息
    masks = [mask[0] for mask in sorted_masks]

    # 使用第一个mask作为初始主要物体mask
    main_object_mask = masks[0].astype(np.uint8)

    # 遍历剩余的mask，将其作为孔洞剔除
    for mask in masks[1:]:
        # 使用cv2.subtract从主要物体mask中去除孔洞
        main_object_mask = cv2.subtract(main_object_mask, mask.astype(np.uint8))

    return main_object_mask


# 展示mask效果
def show_mask(mask, ax, random_color=False):
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        color = np.array([30 / 255, 144 / 255, 255 / 255, 0.6])
    h, w = mask.shape[-2:]
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    ax.imshow(mask_image)


# 获取分割边界轮廓
def get_contours_on_image(mask):
    mask_binary = mask.astype(np.uint8) * 255

    # 图像缩放
    scale_percent = 50
    width = int(mask_binary.shape[1] * scale_percent / 100)
    height = int(mask_binary.shape[0] * scale_percent / 100)
    dim = (width, height)

    mask_binary = cv2.resize(mask_binary, dim, interpolation=cv2.INTER_AREA)
    contours, hierarchy = cv2.findContours(mask_binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    annotated_image = cv2.cvtColor(mask_binary, cv2.COLOR_GRAY2BGR)

    for contour in contours:
        # 获取bounding box坐标
        x, y, w, h = cv2.boundingRect(contour)

        # 画出bounding box
        # cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (255, 0, 0), 2)  # 红色

        # 计算长、宽
        length = w
        width = h
        # cv2.drawContours(annotated_image, [contour], -1, (0, 0, 255), 2)  # 红色，线宽为2
        # 输出bounding box坐标和长宽
        # print(f"Bounding Box: (x:{x}, y:{y}, w:{w}, h:{h}), Length: {length}, Width: {width}")

    # 将布尔类型的掩码转换为整数类型
    mask = mask.astype(np.uint8)

    # cv2.imshow('contours of main part',annotated_image)

    # cv2.waitKey(0)

    # cv2.destroyAllWindows()
    # cv2_imshow(annotated_image)

    # cv2.imwrite("part_annotated_image.jpg", annotated_image)
    return contours, hierarchy


# 去除图像噪声——去除重复叠加轮廓
def remove_duplicate_contours(contours, hierarchy, epsilon=10):
    unique_contours = []
    unique_hierarchy = []
    unique_centroids = []

    for i, contour1 in enumerate(contours):
        is_duplicate = False
        centroid1 = np.mean(contour1, axis=0)[0]

        for j, (contour2, centroid2) in enumerate(zip(unique_contours, unique_centroids)):
            if cv2.matchShapes(contour1, contour2, cv2.CONTOURS_MATCH_I1, 0) < 0.05 and \
                    np.linalg.norm(centroid1 - centroid2) < epsilon:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_contours.append(contour1)
            unique_hierarchy.append(hierarchy[0][i])
            unique_centroids.append(centroid1)

    return unique_contours, [np.array(unique_hierarchy, dtype=np.int32)]


def get_bitImage_byContours(contours, hierarchy, image_size=224, flex_ratio=0):
    # 预留缓冲区间
    contours_size = image_size - 2 * flex_ratio

    # 找到最大边界
    max_x = max_y = 0
    min_x, min_y = float('inf'), float('inf')

    for contour in contours:
        for point in contour[:, 0]:
            if point[0] > max_x:
                max_x = point[0]
            if point[0] < min_x:
                min_x = point[0]
            if point[1] > max_y:
                max_y = point[1]
            if point[1] < min_y:
                min_y = point[1]

    # 计算新图像的尺寸
    width = max_x - min_x
    height = max_y - min_y

    scale = min(contours_size / width, contours_size / height)

    # 计算偏移量
    offset_x, offset_y = min_x - flex_ratio, min_y - flex_ratio

    # 创建一个新的空白图像
    blank_image = np.zeros((image_size, image_size), np.uint8)

    # 将轮廓绘制在新图像上
    for i, contour in enumerate(contours):
        contour_scaled = (contour - (offset_x, offset_y)) * scale
        contour_scaled = contour_scaled.astype(np.int32)

        # 如果轮廓没有父轮廓（即它是外部轮廓），则绘制为白色
        if hierarchy[0][i][3] == -1:
            cv2.drawContours(blank_image, [contour_scaled], -1, (255, 255, 255), thickness=cv2.FILLED)
        else:
            # 如果轮廓有父轮廓（即它是内部孔洞），则绘制为黑色
            cv2.drawContours(blank_image, [contour_scaled], -1, (0, 0, 0), thickness=cv2.FILLED)

    blank_image = Image.fromarray(cv2.cvtColor(blank_image, cv2.COLOR_BGR2RGB))
    return blank_image


def find_outer_contour(contours, hierarchy):
    outer_contours = []
    for i, contour in enumerate(contours):
        if hierarchy[0][i][3] == -1:  # 检查轮廓是否为外部轮廓
            outer_contours.append(contour)
    areas = [cv2.contourArea(contour) for contour in outer_contours]
    return outer_contours[np.argmax(areas)]


def rotate_contours(contours, angle, center):
    rotated_contours = []
    for contour in contours:
        contour = contour.reshape(-1, 2)
        rotated_contour = cv2.transform(contour[None, :, :], cv2.getRotationMatrix2D(center, angle, 1))
        rotated_contours.append(rotated_contour.reshape(-1, 1, 2))
    return rotated_contours


def align_contours(contours1, contours2, hierarchy1, hierarchy2):
    # 找到contours1和contours2的最外层轮廓
    outer_contour1 = find_outer_contour(contours1, hierarchy1)
    outer_contour2 = find_outer_contour(contours2, hierarchy2)

    # 计算最外层轮廓的方向（角度） using image moments
    moments1 = cv2.moments(outer_contour1)
    angle1 = 0.5 * np.arctan2(2 * moments1['mu11'], moments1['mu20'] - moments1['mu02']) * 180 / np.pi

    moments2 = cv2.moments(outer_contour2)
    angle2 = 0.5 * np.arctan2(2 * moments2['mu11'], moments2['mu20'] - moments2['mu02']) * 180 / np.pi

    # 获取旋转中心
    center1 = tuple(np.mean(outer_contour1, axis=0).astype(int).flatten().tolist())
    center2 = tuple(np.mean(outer_contour2, axis=0).astype(int).flatten().tolist())

    # 旋转contours1中的所有轮廓
    rotated_contours1 = rotate_contours(contours1, angle2 - angle1, center1)

    return rotated_contours1, hierarchy1, angle2 - angle1


def calculate_overlap(image1, image2):
    intersection = cv2.bitwise_and(image1, image2)
    area_intersection = np.sum(intersection == 255)

    area_image2 = np.sum(image2 == 255)

    overlap_ratio = area_intersection / area_image2 if area_image2 > 0 else 0
    return overlap_ratio


def find_best_rotation(contours1, hierarchy1, image1, image2):
    image1 = cv2.cvtColor(cv2.cvtColor(np.array(image1), cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2GRAY)
    image2 = cv2.cvtColor(cv2.cvtColor(np.array(image2), cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2GRAY)
    best_overlap = 0
    best_angle = 0
    outer_contour1 = find_outer_contour(contours1, hierarchy1)
    image1 = cv2.cvtColor(cv2.cvtColor(np.array(image1), cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2GRAY)
    center1 = tuple(np.mean(outer_contour1, axis=0).astype(int).flatten().tolist())
    for angle in range(0, 360):
        rotated_contour1 = rotate_contours(contours1, angle, center1)
        image1 = get_bitImage_byContours(rotated_contour1, hierarchy1)
        image1 = cv2.cvtColor(cv2.cvtColor(np.array(image1), cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2GRAY)
        overlap = calculate_overlap(image1, image2)
        if overlap > best_overlap:
            best_overlap = overlap
            best_angle = angle

            # print(best_angle,best_overlap)
    rotated_contour1 = rotate_contours(contours1, best_angle, center1)
    return best_angle, best_overlap, rotated_contour1, hierarchy1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='choose for show features on the image')

    parser.add_argument('-model_id', '--id', dest='model_id', type=str, required=True,
                        help='input your model name space')
    parser.add_argument('-image_path', '-path', dest='image_path', type=str, required=True,
                        help='input the absolute path of your image')
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    generator = pipeline("mask-generation", model=args.model_id, device=device, points_per_batch=256)

    image_url = args.image_path
    preprocessed_image = preprocess_img_byRmBackground(image_url)

    outputs = generator(preprocessed_image, points_per_batch=256)

    # plt.imshow(np.array(raw_image))
    # ax = plt.gca()
    # plt.axis("off")
    main_object_mask = extract_main_object_mask(outputs["masks"])
    contours, hierarchy = get_contours_on_image(main_object_mask)
    # show_mask(main_object_mask, ax=ax)
    # contours,hierarchy=remove_duplicate_contours(contours,hierarchy)
    image = get_bitImage_byContours(contours, hierarchy)

    image.save('show_segment.jpg')
    # features = get_features(contours)
    # print(features)
