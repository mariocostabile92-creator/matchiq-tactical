# MatchIQ Vision Engine V3 - Augmentations

The first football-specific fine-tuning configuration uses only prudent transforms:

- moderate brightness and contrast variation for day/night and shadow changes;
- moderate JPEG compression and light noise for amateur recordings;
- light Gaussian and motion blur for camera movement;
- resize and controlled crop that preserve the labelled object;
- moderate colour jitter and occlusion.

Vertical flips, extreme rotations, severe colour shifts, geometric distortion and crops
that remove most of an object are forbidden. The test split is never augmented.
