# YoutubeThumbnailScoring

Description: The purpose of this project is to train a lightweight nueral net that can help youtubers better understand how sucessful their thubnails will be so they can adapt and improve 
Usage: The dataset file is used to add data to the dataset. Users will need to set up and add their own API key which can be done via the google cloud console and add their own search queries. 

The manualtest.py file is used to test out the network on specific thumbnails. To test different images, simply change the url to the one for the desired thumbnail and run.

The remaining 4 files, are implementations of different networks with various evaluation citeria. Assure the file paths are to the correct amound csvs and that there are the correct amount of classes. ythumbnail.py is an implementation of MobileNetV3Small with top 1 classification on 3 classes. ythumbnailnet_resnet_top_k_error_rate is an implementation of ResNet50 on top 3 classification of 10 classes. ythumbnailnet_efficientnet_top_k_error_rate is an implementation of EfficientNetB3 on top 3 classification of 10 classes. YThumbnailNet_Top_5_25_class_ENB4 is an implementation of EfficientNetB4 on top 5 classification of 25 classes.


I suggest using all of these files in google collab as that is where I set them up and oprated them.
