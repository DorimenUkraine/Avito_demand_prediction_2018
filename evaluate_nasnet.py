import numpy as np
import argparse
from path import Path

from keras.models import Model
from keras.layers import Dense, Dropout
from keras.preprocessing.image import load_img, img_to_array
import tensorflow as tf
import tqdm
from utils.nasnet import NASNetMobile, preprocess_input
from utils.score_utils import mean_score, std_score

parser = argparse.ArgumentParser(description='Evaluate NIMA(Inception ResNet v2)')
parser.add_argument('-dir', type=str, default=None,
                    help='Pass a directory to evaluate the images in it')

parser.add_argument('-img', type=str, default=[None], nargs='+',
                    help='Pass one or more image paths to evaluate them')

parser.add_argument('-rank', type=str, default='true',
                    help='Whether to tank the images after they have been scored')

args = parser.parse_args()
target_size = (224, 224)  # NASNet requires strict size set to 224x224
rank_images = args.rank.lower() in ("true", "yes", "t", "1")

# give priority to directory
if args.dir is not None:
    print("Loading images from directory : ", args.dir)
    imgs = Path(args.dir).files('*.png')
    imgs += Path(args.dir).files('*.jpg')
    imgs += Path(args.dir).files('*.jpeg')

elif args.img[0] is not None:
    print("Loading images from path(s) : ", args.img)
    imgs = args.img

else:
    raise RuntimeError('Either -dir or -img arguments must be passed as argument')

with tf.device('/GPU:0'):
    base_model = NASNetMobile((224, 224, 3), include_top=False, pooling='avg', weights=None)
    x = Dropout(0.75)(base_model.output)
    x = Dense(10, activation='softmax')(x)

    model = Model(base_model.input, x)
    model.load_weights('weights/nasnet_weights.h5')

    score_list = np.empty((len(imgs), 11), dtype=object)
    step = 20000
    i = 0
    while i < len(imgs):
        print(i)
        imgs_temp = imgs[i:i + step]
        img_array = np.empty((len(imgs_temp), 224, 224, 3))
        file_names = []
        for ind, j in tqdm.tqdm(enumerate(imgs_temp)):
            x = preprocess_input(np.expand_dims(img_to_array(load_img(j, target_size=target_size)), axis=0))
            img_array[ind, ] = x
            file_names.append(Path(j).name.lower())

        scores = model.predict(img_array, batch_size=100, verbose=0)
        score_list[i:i + step, 0] = file_names
        score_list[i:i + step, 1:] = scores
        i += step

        np.save('nasnet_scores_test.npy', score_list)