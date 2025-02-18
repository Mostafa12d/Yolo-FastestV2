import os
import cv2
import time
import argparse

import torch
import model.detector
import utils.utils

if __name__ == '__main__':
    #Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='', 
                        help='Specify training profile *.data')
    parser.add_argument('--weights', type=str, default='', 
                        help='The path of the .pth model to be transformed')
    parser.add_argument('--img', type=str, default='', 
                        help='The path of test image')

    opt = parser.parse_args()
    cfg = utils.utils.load_datafile(opt.data)
    # print("cfg:", cfg)
    # exit(0)
    assert os.path.exists(opt.weights), "Please specify the correct model path"
    assert os.path.exists(opt.img), "Please specify the correct test image path"

    #Load model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.detector.Detector(cfg["classes"], cfg["anchor_num"], True).to(device)
    model.load_state_dict(torch.load(opt.weights, map_location=device))

    #sets the module in eval node
    model.eval()
    
    #Capture video through webcam
    cap = cv2.VideoCapture(0)
    time.sleep(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 800)

    while True:
        print('-----------------------------------------------------')    
        ret, ori_img = cap.read()
        if ori_img is None:
            continue
        res_img = cv2.resize(ori_img, (cfg["width"], cfg["height"]), interpolation = cv2.INTER_LINEAR) 
        img = res_img.reshape(1, cfg["height"], cfg["width"], 3)
        img = torch.from_numpy(img.transpose(0,3, 1, 2))
        img = img.to(device).float() / 255.0  
        preds = model(img)
        output = utils.utils.handel_preds(preds, cfg, device)
        output_boxes = utils.utils.non_max_suppression(output, conf_thres = 0.3, iou_thres = 0.4)
        LABEL_NAMES = []
        with open(cfg["names"], 'r') as f:
            for line in f.readlines():
                LABEL_NAMES.append(line.strip())
                
        h, w, _ = ori_img.shape
        scale_h, scale_w = h / cfg["height"], w / cfg["width"]
        for box in output_boxes[0]:
            box = box.tolist()
            
            obj_score = box[4]
            category = LABEL_NAMES[int(box[5])]

            x1, y1 = int(box[0] * scale_w), int(box[1] * scale_h)
            x2, y2 = int(box[2] * scale_w), int(box[3] * scale_h)
            print("x1, y1, x2, y2:", x1, y1, x2, y2)

            cv2.rectangle(ori_img, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(ori_img, '%.2f' % obj_score, (x1, y1 - 5), 0, 0.7, (0, 255, 0), 2)	
            cv2.putText(ori_img, category, (x1, y1 - 25), 0, 0.7, (0, 255, 0), 2)
        cv2.imshow("", ori_img)     
        if (cv2.waitKey(1) & 0xFF == ord("q")) or (cv2.waitKey(1)==27):
            break
    cap.release()
    cv2.destroyAllWindows()
   