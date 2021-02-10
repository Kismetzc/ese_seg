＃＃　修改的内容
＃　１　gluon-cv/gluoncv/data/pascal_voc/detection.py　
            line49,198,349,  modify root =   
                root = '/home/alex/Desktop/ese-seg/data'

#   2  sbd_train_che_8.py line 39
        with cpu 
            python sbd_train_che_8.py --syncbn --network darknet53 --batch-size 20 --dataset voc --gpus 0 --warmup-epochs 10 --save-prefix ./darknet53_result
            

