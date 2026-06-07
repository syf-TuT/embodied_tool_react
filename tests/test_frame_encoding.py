import unittest

import numpy as np

from embodied_agent.observers.frame_encoding import encode_frame_jpeg_data_url


class FrameEncodingTests(unittest.TestCase):
    def test_none_frame_returns_none(self):
        self.assertIsNone(encode_frame_jpeg_data_url(None))

    def test_rgb_uint8_frame_returns_jpeg_data_url(self):
        frame = np.array(
            [
                [[255, 0, 0], [0, 255, 0]],
                [[0, 0, 255], [255, 255, 255]],
            ],
            dtype=np.uint8,
        )

        data_url = encode_frame_jpeg_data_url(frame)

        self.assertIsInstance(data_url, str)
        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))
        self.assertGreater(len(data_url), 40)


if __name__ == "__main__":
    unittest.main()
