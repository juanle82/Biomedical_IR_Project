#include <iostream>
#include <string>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/objdetect.hpp>

using namespace cv;
using namespace std;

namespace cd
{
    typedef enum e_CameraType {Visible, IR} CameraType;

    class CameraDetector
    {
    public:

        int DetectCameraID(CameraType cameraType)
        {
            for (size_t i = 0; i < 16; i++)
            {
                try
                {
                    VideoCapture vc(i);
                    Mat img;

                    vc.read(img);
                    if((Size2d)img.size() == cameraSizes[(int)cameraType])
                    {
                        cout << "Camera " << cameraType << " found in index " << i << endl;
                        return i;
                    }
                }
                catch(const std::exception& e)
                {
                    continue;
                }      
            }
            
            return -1;
        }

        void AdjustImage(Mat & img, int xOffset[2], int yOffset[2], Size2d imgSize)
        {
            Rect roi = Rect(xOffset[0], yOffset[0], img.cols-xOffset[0]-xOffset[1], img.rows-yOffset[0]-yOffset[1]);
            
            Mat temp;
            img(roi).copyTo(temp);

            resize(temp, temp, imgSize);
            img = temp.clone();
        }

    private:
        Size2d cameraSizes[2] = {Size2d(640, 480), Size2d(160, 120)};
        
    };
}
