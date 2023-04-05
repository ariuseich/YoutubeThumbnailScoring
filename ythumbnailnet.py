# -*- coding: utf-8 -*-
"""YThumbnailNet

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/18zaFe02svxqrqiSZHNLu0329JohGu6J7
"""

!pip install torch torchvision
!pip install pytz
!pip install requests

# Commented out IPython magic to ensure Python compatibility.
from google.colab import drive
drive.mount('/content/drive')

# %cd '/content/drive/MyDrive/YTScoringDataSet/CSV Databases/'
!ls
folderPath = '/content/drive/MyDrive/YTScoringDataSet/CSV Databases/'

#label the data
import pandas as pd
import pytz
from datetime import datetime

def process_csv_and_label_data(input_csv_path, output_csv_path, line_1, line_2):
    # 1. Load the CSV
    df = pd.read_csv(input_csv_path)
    #df = pd.read_csv(output_csv_path, dtype={2: 'int64'})

    # Convert 'view_count' to a numeric type
    df['view_count'] = pd.to_numeric(df['view_count'], errors='coerce')

    # 3. Calculate views_per_day
    df['views_per_day'] = df['view_count'] / df['days_published']

    # 4. Label the data based on views_per_day
    df['label'] = df['views_per_day'].apply(lambda x: 0 if x <= line_1 else (1 if x < line_2 else 2))

    # Save the CSV to a new file
    df.to_csv(output_csv_path, index=False)

def count_classes(output_csv_path):
    df = pd.read_csv(output_csv_path)
    
    num_class_0 = (df['label'] == 0).sum()
    num_class_1 = (df['label'] == 1).sum()
    num_class_2 = (df['label'] == 2).sum()

    total = num_class_0 + num_class_1 + num_class_2
    print("Class distribution:\nClass 0: {}\t\t{}%\nClass 1: {}\t\t{}%\nClass 2: {}\t\t{}%".format(num_class_0, num_class_0/total*100, num_class_1, num_class_1/total*100, num_class_2, num_class_2/total*100))


# Example usage
input_csv_path = 'Copy_of_youtube_video_data4.1.csv'
output_csv_path = 'youtube_video_data_labeled.csv'
process_csv_and_label_data(input_csv_path, output_csv_path, 5, 175)
count_classes(output_csv_path)

import os
import pandas as pd
from PIL import Image
import torch
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import requests
from io import BytesIO
from torch.utils.data import random_split

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set your CSV file path and the column names for image URLs and labels
csv_file_path = output_csv_path
image_url_column = "thumbnail_url"
label_column = "label"

# Define the transformations
transform = transforms.Compose([
    transforms.Resize(256),  # Resize the images to 256x256 pixels
    transforms.CenterCrop(224),  # Center crop the images to 224x224 pixels
    transforms.ToTensor(),  # Convert images to PyTorch tensors
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # Normalize using the ImageNet mean and standard deviation
])

# Create a custom Dataset class
class ImageDataset(Dataset):
    def __init__(self, csv_file, image_url_column, label_column, transform=None):
        self.data = pd.read_csv(csv_file)
        self.image_urls = self.data[image_url_column]
        self.labels = self.data[label_column]
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_url = self.image_urls[idx]
        
        try:
            # Download the image using requests
            response = requests.get(img_url)
            img = Image.open(BytesIO(response.content)).convert('RGB')
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image at URL: {img_url}")
            return None, None
        
        if self.transform:
            img = self.transform(img)

        label = self.labels[idx]
        return img, label

# Load the dataset
dataset = ImageDataset(csv_file_path, image_url_column, label_column, transform=transform)

# Split the dataset into 80/20 train/test sets
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_dataset, test_dataset = random_split(dataset, [train_size, test_size])

# Create DataLoaders for the train and test sets
batch_size = 32  # You can adjust the batch size according to your requirements
suggested_num_workers = 2  # Set the suggested number of workers
train_data_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=suggested_num_workers)
test_data_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=suggested_num_workers)

import torch
import torch.optim as optim
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_small

# Set up the device (CPU or GPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load the model and modify the classifier
num_classes = 3
model = mobilenet_v3_small(weights=True)
model.classifier[-1] = torch.nn.Linear(in_features=1024, out_features=num_classes)
model = model.to(device)

# Set up the loss function and optimizer
criterion = torch.nn.CrossEntropyLoss()
optimizer = optim.AdamW(model.parameters(), lr=0.001)

# Set up the training loop
num_epochs = 3  # Adjust the number of epochs according to your requirements
for epoch in range(num_epochs):
    running_loss = 0.0
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

        # Calculate the number of images processed
        total_images += images.size(0)

        # Print average loss for every 1000 images
        if total_images % 250 == 0:
            print(f"Processed {total_images} images - Average Loss: {running_loss / (i + 1)}")

    # Print the average loss for this epoch
    print(f"Epoch {epoch + 1}, Loss: {running_loss / (i + 1)}")

    # Save the model weights
    model_weights_path = "model_weights.pth"
    torch.save(model.state_dict(), model_weights_path)
    print("Model weights saved.")


print("Training finished.")

def test(model, test_data_loader, device):
    model.eval()  # Set the model to evaluation mode

    correct = 0
    total = 0

    with torch.no_grad():  # Disable gradient calculations
        for images, labels in test_data_loader:
            if images is None or labels is None:
                continue

            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)

            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy_rate = 100 * correct / total
    print(f"Accuracy Rate: {accuracy_rate:.2f}%")


# Call the test function
test(model, test_data_loader, device)

import torch
from torchvision.models import mobilenet_v3_small

num_classes = 3
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def test(model, test_data_loader, device):
    model.eval()  # Set the model to evaluation mode

    correct = 0
    total = 0

    with torch.no_grad():  # Disable gradient calculations
        for images, labels in test_data_loader:
            if images is None or labels is None:
                continue

            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)

            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy_rate = 100 * correct / total
    print(f"Accuracy Rate: {accuracy_rate:.2f}%")



# Define your model architecture
model = mobilenet_v3_small(weights=True)
model.classifier[-1] = torch.nn.Linear(in_features=1024, out_features=num_classes)

# Load saved model weights
weights = torch.load("model_weights4.4.pth")
model.load_state_dict(weights)

# Move the model to the device
model.to(device)

# Call the test function
test(model, test_data_loader, device)