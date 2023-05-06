# -*- coding: utf-8 -*-
"""YThumbnailNet EfficientNet Top K Error Rate

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ilJM6B-xr4UG87Du7AvCI56xxgk7VCp8
"""

# Commented out IPython magic to ensure Python compatibility.
from google.colab import drive
drive.mount('/content/drive')

# %cd '/content/drive/MyDrive/YTScoringDataSet/CSV Databases/'
#!ls
folderPath = '/content/drive/MyDrive/YTScoringDataSet/CSV Databases/'

!pip install efficientnet_pytorch

import os
import pandas as pd
from PIL import Image
import torch
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import requests
from io import BytesIO
from torch.utils.data import random_split
import numpy as np

output_csv_paths = ['youtube_video_data_labeled_1_multiclass.csv', 'youtube_video_data_labeled_2_multiclass.csv', 
                    'youtube_video_data_labeled_3_multiclass.csv', 'youtube_video_data_labeled_4_multiclass.csv']

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set the column names for image URLs and labels
image_url_column = "thumbnail_url"
label_column = "label"

# Define the transformations
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def count_unique_labels(dataset):
    return len(dataset.labels.unique())

# Create a custom Dataset class
class ImageDataset(Dataset):
    def __init__(self, csv_files, image_url_column, label_column, transform=None):
        self.data = pd.concat([pd.read_csv(csv_file) for csv_file in csv_files], ignore_index=True)
        self.image_urls = self.data[image_url_column]
        self.labels = self.data[label_column]
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_url = self.image_urls[idx]

        try:
            response = requests.get(img_url)
            img = Image.open(BytesIO(response.content)).convert('RGB')
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image at URL: {img_url}")
            return None, None

        if self.transform:
            img = self.transform(img)

        label = self.labels[idx]
        return img, label

# Set the random seed for reproducibility
random_seed = 42
np.random.seed(random_seed)
torch.manual_seed(random_seed)

# Load the dataset
dataset = ImageDataset(output_csv_paths, image_url_column, label_column, transform=transform)

# Split the dataset into 80/20 train/test sets
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_dataset, test_dataset = random_split(dataset, [train_size, test_size])
print(len(dataset))

# Create DataLoaders for the train and test sets
batch_size = 32
suggested_num_workers = 2
train_data_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=suggested_num_workers)
test_data_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=suggested_num_workers)

import torch
import torch.optim as optim
import torch.nn.functional as F
from efficientnet_pytorch import EfficientNet

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

model = EfficientNet.from_pretrained('efficientnet-b3', num_classes=1)
model = model.to(device)

criterion = torch.nn.MSELoss()
optimizer = optim.AdamW(model.parameters(), lr=0.001)

def top_k_accuracy(output, target, k):
    batch_size = target.size(0)
    _, pred = output.topk(k, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))
    correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)

# Set up the training loop
num_epochs = 10  # Adjust the number of epochs according to your requirements
for epoch in range(num_epochs):
    running_loss = 0.0
    running_top1_error = 0.0
    running_top2_error = 0.0
    running_top3_error = 0.0
    total_images = 0
    for i, (images, labels) in enumerate(train_data_loader):
        if images is None or labels is None:
            continue

        # Move the images and labels to the GPU if available
        images = images.to(device)
        labels = labels.to(device)

        # Reset the gradients of the optimizer
        optimizer.zero_grad()

        # Forward pass through the model
        outputs = model(images)

        # Calculate the loss
        loss = criterion(outputs, labels)

        # Backward pass to compute gradients
        loss.backward()

        # Update the model parameters
        optimizer.step()

        # Accumulate the loss for this epoch
        running_loss += loss.item()

        # Calculate top-k accuracy and error rates
        top1_acc = top_k_accuracy(outputs, labels, 1)
        top2_acc = top_k_accuracy(outputs, labels, 2)
        top3_acc = top_k_accuracy(outputs, labels, 3)
        running_top1_error += 100.0 - top1_acc.item()
        running_top2_error += 100.0 - top2_acc.item()
        running_top3_error += 100.0 - top3_acc.item()

        # Calculate the number of images processed
        total_images += images.size(0)

        # Print average loss and error rates for every 1000 images
        if total_images % 1000 == 0:
            print(f"Processed {total_images} images - Average Loss: {running_loss / (i + 1)}, "
                  f"Top-1 Accuracy: {100 - running_top1_error / (i + 1)}, "
                  f"Top-2 Accuracy: {100 - running_top2_error / (i + 1)}, "
                  f"Top-3 Accuracy: {100 - running_top3_error / (i + 1)}")

    # Print the average loss and error rates for this epoch
    print(f"Epoch {epoch + 1}, Loss: {running_loss / (i + 1)}, "
          f"Top-1 Error: {100 - running_top1_error / (i + 1)}, "
          f"Top-2 Error: {100 - running_top2_error / (i + 1)}, "
          f"Top-3 Error: {100 - running_top3_error / (i + 1)}")

    # Save the model weights
    model_weights_path = "model_weights_multi_guess.pth"
    torch.save(model.state_dict(), model_weights_path)
    print("Model weights saved.")

print("Training finished.")

def test(model, test_data_loader, device, k=3):
    model.eval()  # Set the model to evaluation mode

    correct_k = 0
    total = 0

    with torch.no_grad():  # Disable gradient calculations
        for images, labels in test_data_loader:
            if images is None or labels is None:
                continue

            images, labels = images.to(device), labels.to(device)

            outputs = model(images)

            # Calculate top-k accuracy
            correct_k += top_k_accuracy(outputs, labels, k).item()

            total += labels.size(0)

    accuracy_rate = correct_k / total
    error_rate = 100 - accuracy_rate
    print(f"Top-{k} Accuracy Rate: {accuracy_rate:.2f}%")
    print(f"Top-{k} Error Rate: {error_rate:.2f}%")


# Call the test function with the desired value of k
test(model, test_data_loader, device, k=3)

import torch
from torchvision.models import resnet50

num_classes = count_unique_labels(dataset)
print("Number of classes: ", num_classes)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

def top_k_accuracy(output, target, k):
    batch_size = target.size(0)
    _, pred = output.topk(k, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))
    correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
    return correct_k.mul_(100.0 / batch_size)

def test(model, test_data_loader, device, k=3):
    model.eval()  # Set the model to evaluation mode

    correct_k = 0
    total = 0

    with torch.no_grad():  # Disable gradient calculations
        for images, labels in test_data_loader:
            if images is None or labels is None:
                continue

            images, labels = images.to(device), labels.to(device)

            outputs = model(images)

            # Calculate top-k accuracy
            correct_k += top_k_accuracy(outputs, labels, k).item()

            total += labels.size(0)

    accuracy_rate = correct_k / total
    error_rate = 100 - accuracy_rate
    print(f"Top-{k} Accuracy Rate: {accuracy_rate:.2f}%")
    print(f"Top-{k} Error Rate: {error_rate:.2f}%")

# Define your model architecture
model = resnet50(pretrained=True)
model.fc = torch.nn.Linear(in_features=2048, out_features=num_classes)

# Load saved model weights
weights = torch.load("model_weights_multi_guess.pth")
model.load_state_dict(weights)

# Move the model to the device
model.to(device)

# Call the test function with the desired value of k
test(model, test_data_loader, device, k=3)



''' if you need to test the a parallelized model
from collections import OrderedDict

# Load saved model weights
weights = torch.load("model_weights(4.15SCC).pth")

# Remove 'module.' prefix from the keys in the saved weights
new_weights = OrderedDict()
for key, value in weights.items():
    new_key = key.replace("module.", "")
    new_weights[new_key] = value

# Load the new weights into the model
model.load_state_dict(new_weights)

# Move the model to the device
model.to(device)

# Call the test function
test(model, test_data_loader, device)
'''