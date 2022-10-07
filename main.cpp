#include <iostream>
#include <string>
#include <cassert>
#include <iterator>
#include <fstream>
#include <unistd.h>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/objdetect.hpp>
#include "Calib.hpp"


using namespace cv;
using namespace std;
using namespace cd;

#define T1  36.0
#define T2  36.04 //37.1
#define R1  8250
#define R2  8400
#define IRSensorTo8Bit  16383.0/255
#define TEXTOFFSET Point(32,-12)

void OnMouseIR(int, int, int, int, void*);
void OnMouseVisible(int, int, int, int, void*);
void OnMouseCalib(int, int, int, int, void*);
void colorReduce(Mat&, int);
double GetTempFromIRImage(const Mat&, const Rect&, bool, double*);
double IRtoTempComversion(const double&);
double ApplySegmentation(const Mat&, Mat&);
void SaveImages(CameraType);
void DrawSaveButton(Mat);
bool LoadConfig();

bool freeze = false;
bool drawing = false;
bool calibMode = false;

// Default configuration.
int imgWidth = 512;
int imgHeight = 384;
int xOffset[2] = {80, 33};
int yOffset[2] = {55, 28};
Size2d imgSize = Size2d(imgWidth, imgHeight);
int areaThreshold = 400;
int grayLevelsReduction = 32; 

CameraDetector cD;
VideoCapture IRVC(cD.DetectCameraID(CameraType::IR));
VideoCapture VVC(cD.DetectCameraID(CameraType::Visible));

class UserData
{
    public:

        Mat IR;
        Mat C;
        vector<vector<Point>> contours;

        UserData() {};
        UserData(Mat IR, Mat C, vector<vector<Point>> contours) : IR(IR), C(C), contours(contours) {}
};

int main (int argc, char *argv[])
{
    Mat imgIR,imgIRraw, imgPre, imgCanny, imgV;
    Mat test(imgSize, CV_8UC3, Scalar(0,0,0));
    UserData userdata;

    LoadConfig();

    // Crea ventanas   
    namedWindow("Visible Image", WINDOW_AUTOSIZE);
    namedWindow("IR Image", WINDOW_AUTOSIZE);

    // namedWindow("calibration", WINDOW_AUTOSIZE);
    // createTrackbar("x1", "calibration", &xOffset[0], 150);
    // createTrackbar("x2", "calibration", &xOffset[1], 150);
    // createTrackbar("y1", "calibration", &yOffset[0], 150);
    // createTrackbar("y2", "calibration", &yOffset[1], 150);


    while (true)
    {
        // If IR window was closed
        if(getWindowProperty("IR Image", WND_PROP_FULLSCREEN) == -1)
            return 1;

        // If Visible window was closed
        if(getWindowProperty("Visible Image", WND_PROP_FULLSCREEN) == -1)
            return 1;

        if(!freeze && !drawing)
        {
            if(grayLevelsReduction <= 0) 
                grayLevelsReduction = 1;

            VVC.read(imgV);
            resize(imgV, imgV, imgSize);
            cD.AdjustImage(imgV, xOffset, yOffset, imgSize);

            IRVC.read(imgIR);
            resize(imgIR, imgIR, imgSize);
            IRVC.read(imgIRraw);

            GaussianBlur(imgIR, imgPre, Size(5,5), 0, 0, BORDER_DEFAULT);
            cvtColor(imgPre, imgPre, COLOR_BGR2GRAY);
            threshold(imgPre, imgPre, 115, 250, THRESH_TOZERO);

            colorReduce(imgPre, grayLevelsReduction);
            
            Canny(imgPre, imgCanny, 50, 70);
            Mat kernel = getStructuringElement(MORPH_RECT, Size(2,2));
            dilate(imgCanny, imgCanny, kernel);  

            vector<vector<Point>> contours;
            vector<vector<Point>> closedContours;
            vector<Vec4i> hierarchy;
            findContours(imgCanny, contours, hierarchy, RETR_TREE, CHAIN_APPROX_SIMPLE);

            // Save button graphics
            DrawSaveButton(imgIR);
            DrawSaveButton(imgV);

            //Draw the contours
            Mat contourImage(imgCanny.size(), CV_8U, Scalar(0,0,0));

            for (size_t idx = 0, i = 0; idx < contours.size(); idx++) 
            {
                double area = contourArea(contours[idx]);
                if(area < areaThreshold)
                    continue;       

                if(area < arcLength(contours[idx], true)) // Detecta contornos abiertos
                {
                    continue;
                }

                Mat contoursBGR;
                cvtColor(contourImage, contoursBGR, COLOR_GRAY2BGR);
                add(imgIR, contoursBGR, test);

                drawContours(contourImage, contours, idx, Scalar(255,255,255), 1, 8, hierarchy);
                kernel = getStructuringElement(MORPH_RECT, Size(1,1));
                dilate(contourImage, contourImage, kernel);

                Moments m = moments(contours[idx]);
                Point p(m.m10/m.m00, m.m01/m.m00);
            
                putText(contourImage, to_string(i), p, FONT_HERSHEY_PLAIN, 0.8, Scalar(255,255,255));
                closedContours.push_back(contours[idx]);
                i++;
            }

            userdata = UserData(imgIR, contourImage, closedContours);

            imshow("IR Image", test);
            imshow("Visible Image", imgV);
        }

        setMouseCallback("IR Image", OnMouseIR, &userdata);
        setMouseCallback("Visible Image", OnMouseVisible, NULL);

        waitKey(1);
    }
    
}

bool LoadConfig()
{
    try
    {
        FileStorage fs("/home/pi/Documents/tests/biomedicSystem/config.yml", FileStorage::READ);

        bool calibMode = (bool)(int)fs["calibMode"];

        imgWidth = (int)fs["width"];
        imgHeight = (int)fs["height"];
        imgSize = Size2d(imgWidth, imgHeight);

        xOffset[0] = (int)fs["leftOffset"];
        xOffset[1] = (int)fs["rightOffset"];
        yOffset[0] = (int)fs["topOffset"];
        yOffset[1] = (int)fs["bottomOffset"];

        areaThreshold = (int)fs["areaThreshold"];
        grayLevelsReduction = (int)fs["grayLevelsReduction"];

        return calibMode;    
    }
    catch(const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        cout << "Configuration couldn't be loaded. Loading default configuration..." << endl;
        return false;
    }
}

void DrawSaveButton(Mat img)
{
    rectangle(img, Rect(imgWidth - 80, imgHeight - 32, 80, 32), Scalar(255,255,255), FILLED);
    putText(img, "SAVE", Point(imgWidth-65, imgHeight-10), FONT_HERSHEY_PLAIN, 1.3, Scalar(0,0,0), 1, LINE_AA);
}

void SaveImages(CameraType cT = CameraType::IR)
{
    Mat IRSaveImg, IRSaveImgRaw, VSaveImg;
    char image_name[100];
    int image_index=0;
    int i=0;
    static unsigned int IR_raw_image[200][200];
    IRVC.read(IRSaveImg);
    IRVC.read(IRSaveImgRaw);
    resize(IRSaveImg, IRSaveImg, imgSize);
    VVC.read(VSaveImg);

    auto clock = chrono::system_clock::now();
    auto date = chrono::system_clock::to_time_t(clock);
    string dateStr = ctime(&date);
  

   do {
       sprintf(image_name,"/home/pi/Desktop/Capturas/IMG_%.1d.csv",image_index+1);
       image_index += 1;

   } while (access(image_name, F_OK) == 0);

    
    
    string image_num=to_string(image_index);
    
    string dir = "/home/pi/Desktop/Capturas/";
    string IRStr = dir  + "IMG_IR_" + image_num + ".png";
    string VStr = dir  + "IMG_V_" + image_num +".png";
    
    cD.AdjustImage(VSaveImg, xOffset, yOffset, imgSize);

    imwrite(IRStr, IRSaveImg);
    imwrite(VStr, VSaveImg);
   
    ofstream myfile;
    myfile.open(image_name);
    myfile<< cv::format(IRSaveImgRaw, cv::Formatter::FMT_CSV) << std::endl;
    myfile.close();
    
  

   //cv::FileStorage file(image_name, cv::FileStorage::WRITE);
    
    //file << "RawData" << IRSaveImgRaw;

    Mat greenImg = IRSaveImg.clone();
    rectangle(greenImg, Rect(0,0,greenImg.cols, greenImg.rows), Scalar(80,255,0), FILLED);
    
    if(cT == CameraType::IR)
        imshow("IR Image", greenImg);
    else
        imshow("Visible Image", greenImg);

    waitKey(150);
    freeze = false;
    drawing = false;
}

void OnMouseVisible(int event, int x, int y, int flags, void*userdata)
{
    if(event == EVENT_LBUTTONDOWN && (x < imgWidth && x > imgWidth - 80 && y < imgHeight && y > imgHeight - 32))
    {
        SaveImages(CameraType::Visible);
        return;
    }
    if(freeze && event == EVENT_LBUTTONDOWN)
    {
        freeze = false;
        return;
    }
}

void OnMouseIR(int event, int x, int y, int flags, void*userdata)
{ 
    static Point initialP;
    static Rect drawROI;
    static bool dragging = false;

    UserData *data = (UserData *)userdata;
    Mat IR = data->IR;
    vector<vector<Point>> contours = data->contours;

    Mat test(imgSize, CV_8UC3, Scalar(0,0,0));

    // Save button was pressed
    if(event == EVENT_LBUTTONDOWN && (x < imgWidth && x > imgWidth - 80 && y < imgHeight && y > imgHeight - 32))
    {
        SaveImages(CameraType::IR);
        return;
    }

    if(!freeze)
    {
        if (event == EVENT_LBUTTONDBLCLK)
        {
            Point p = Point(x, y);

            if(x > IR.cols || x < 0 || y > IR.rows || y < 0)
                return;

            if(drawing)
                drawing = false;

            for (size_t i = 0; i < contours.size(); i++)
            {
                try
                {
                    double res = pointPolygonTest(contours[i], p, false);
                    if(res == 1)
                    {
                        Rect ROI = boundingRect(contours[i]);

                        Mat mask(IR.size(), CV_8U, Scalar(0,0,0));;
                        drawContours(mask, contours, i, Scalar(255,255,255), FILLED);

                        Mat zone(mask.size(), CV_8UC3, Scalar(0,0,0));
                        bitwise_and(IR, IR, zone, mask);
                        //imshow("Zone", zone(ROI));             

                        Mat IRMatBW;
                        cvtColor(IR, IRMatBW, COLOR_BGR2GRAY);             
                        double otsuThreshold = 0;
                        double meanTemp = GetTempFromIRImage(IRMatBW, ROI, true, &otsuThreshold); 
                        double area = contourArea(contours[i]);                    

                        Mat temp;
                        subtract(IRMatBW, mask, temp);
                        cvtColor(temp, temp, COLOR_GRAY2BGR);
                        add(temp, zone, test);

                        char tempStr[16] = "", areaStr[16] = "";
                        std::sprintf(tempStr, "T=%.2f", (float)meanTemp);
                        std::sprintf(areaStr, "A=%.1f", (float)area);
                        putText(test, tempStr, p - TEXTOFFSET, FONT_HERSHEY_PLAIN, 1, Scalar(0,255,100), 1, LINE_AA);
                        putText(test, areaStr, p - Point(0, 16) - TEXTOFFSET, FONT_HERSHEY_PLAIN, 1, Scalar(0,255,100), 1, LINE_AA);

                        std::cout << areaStr << endl;
                        std::cout << tempStr << endl;   
                        
                        DrawSaveButton(test);
                        imshow("IR Image", test);

                        ////////////////VISIBLE////////////////
                        
                        Mat visImg;
                        VVC.read(visImg);
                        resize(visImg, visImg, imgSize);
                        try
                        {
                            cD.AdjustImage(visImg, xOffset, yOffset, imgSize);
                            // AdjustVImage(visImg);

                            rectangle(visImg, ROI, Scalar(255,255,255));
                            DrawSaveButton(visImg);
                            imshow("Visible Image", visImg);
                        }
                        catch(const std::exception& e)
                        {
                            std::cerr << e.what() << '\n';
                        }                 

                        

                        freeze = true;
                        break;
                    }     
                }
                catch(const std::exception& e)
                {
                    std::cerr << e.what() << '\n';
                }    
            }
        }
        else if(event == EVENT_LBUTTONDOWN)
        {
            initialP = Point(x,y);
            drawing = true;
        }
        else if(event == EVENT_MOUSEMOVE && drawing)
        {            
            dragging = true;
            Point finalPoint = Point(x,y);
            IR.copyTo(test);

            if(x > IR.cols)
                finalPoint.x = IR.cols;
            if(x < 0)
                finalPoint.x = 0;
            if(y > IR.rows)
                finalPoint.y = IR.rows;
            if(y < 0)
                finalPoint.y = 0;

            drawROI = Rect(initialP, finalPoint);
            rectangle(test, drawROI, Scalar(255,255,255), 1);
            imshow("IR Image", test);
        }
        else if(event == EVENT_LBUTTONUP)
        {
            drawing = false;

            if(dragging)
            {
                Mat IRBW, zone;
                char tempStr[16] = "", areaStr[16] = "";

                IR(drawROI).copyTo(zone);
                cvtColor(IR, IRBW, COLOR_BGR2GRAY);

                double thresh = 0;
                Mat ImgSegmented, mask, maskedColor, maskBig(imgSize, CV_8U, Scalar(0,0,0)), temp(imgSize, CV_8U, Scalar(0,0,0));

                try
                {
                    thresh = ApplySegmentation(IRBW(drawROI), ImgSegmented);
                    threshold(ImgSegmented, mask, thresh, 255, THRESH_BINARY);

                    mask.copyTo(maskBig(drawROI));

                    subtract(IRBW, maskBig, temp);
                    cvtColor(temp, temp, COLOR_GRAY2BGR);

                    IR.copyTo(maskedColor, maskBig);
                    add(temp, maskedColor, test);

                    double otsuThreshold = 0;
                    double meanTemp = GetTempFromIRImage(IRBW, drawROI, true, &otsuThreshold); 

                    vector<vector<Point>> maskContours;
                    findContours(mask, maskContours, RETR_TREE, CHAIN_APPROX_SIMPLE);

                    double area = 0;
                    for (size_t i = 0; i < maskContours.size(); i++) 
                    {
                        area += contourArea(maskContours[i]);                              
                    }

                    std::sprintf(tempStr, "T=%.2f", (float)meanTemp);
                    std::sprintf(areaStr, "A=%.1f", (float)area);

                    Point p = Point(drawROI.x + drawROI.width/2, drawROI.y + drawROI.height/2);
                    putText(test, tempStr, p, FONT_HERSHEY_PLAIN, 1, Scalar(0,255,100));
                    putText(test, areaStr, p - Point(0, 16), FONT_HERSHEY_PLAIN, 1, Scalar(0,255,100));

                    DrawSaveButton(test);
                    imshow("IR Image", test);

                    Mat visImg;
                    VVC.read(visImg);
                    resize(visImg, visImg, imgSize);
                    try
                    {
                        cD.AdjustImage(visImg, xOffset, yOffset, imgSize);
                        // AdjustVImage(visImg);

                        rectangle(visImg, drawROI, Scalar(255,255,255));
                        DrawSaveButton(visImg);
                        imshow("Visible Image", visImg);
                    }
                    catch(const std::exception& e)
                    {
                        std::cerr << e.what() << '\n';
                    }     
                }
                catch(const std::exception& e)
                {
                    std::cerr << e.what() << '\n';
                }  

                freeze = true;
            }
            
            dragging = false;
        }
    }
    else if(event == EVENT_LBUTTONDOWN)
    {
        freeze = false;
    }
}

double GetTempFromIRImage(const Mat& Image, const Rect& ROI, bool applySegmentation, double* otsuThreshold)
{
    
    double IR = 0, temperature = 0, threshold;
    Mat ImgROI = Image(ROI);

    if(applySegmentation)
    {
        Mat ImgSegmented;
        threshold = ApplySegmentation(ImgROI, ImgSegmented); // Apply Otsu segmentation.
        IR = mean(ImgSegmented)[0]; // Compute the mean of the segmented image.
    }
    else
    {
        IR = mean(ImgROI)[0]; // Compute the mean of the non-segmented image.
    }

    temperature = IRtoTempComversion(IR); // Convert mean radiation value to mean temperature value.

    if(otsuThreshold != 0)
    {
        *otsuThreshold = threshold; // Return thresh value by ref.
    }

    return temperature; // Return the mean temperature.
}

double IRtoTempComversion(const double& IR)
{    
    double a, b;

    a = (T2-T1)/(R2-R1);
    b = T2 - a*R2;

    return IR*IRSensorTo8Bit*a + b;
}

double ApplySegmentation(const Mat& Image, Mat& result)
{
    return threshold(Image, result, 0, 0, THRESH_TOZERO | THRESH_OTSU);
}

void colorReduce(Mat& image, int div=64)
{    
    int nl = image.rows;                    // Number of lines
    int nc = image.cols * image.channels(); // Number of elements per line

    for (int j = 0; j < nl; j++)
    {
        // Get the address of row j
        uchar* data = image.ptr<uchar>(j);

        for (int i = 0; i < nc; i++)
        {
            // Process each pixel
            data[i] = data[i] / div * div + div / 2;
        }
    }
}

void OnMouseCalib(int event, int x, int y, int flags, void*userdata)
{
    static Point initialP;
    static Rect drawROI;
    static bool dragging = false;
    Mat IR = *(Mat *)userdata;
    Mat test(imgSize, CV_8UC3, Scalar(0,0,0));

    if(freeze && event == EVENT_LBUTTONDOWN)
    {
        freeze = false;
    }
    else if(event == EVENT_LBUTTONDOWN)
    {
        initialP = Point(x,y);
        drawing = true;
    }
    else if(event == EVENT_MOUSEMOVE && drawing)
    {            
        dragging = true;
        Point finalPoint = Point(x,y);
        IR.copyTo(test);

        if(x > IR.cols)
            finalPoint.x = IR.cols;
        if(x < 0)
            finalPoint.x = 0;
        if(y > IR.rows)
            finalPoint.y = IR.rows;
        if(y < 0)
            finalPoint.y = 0;

        drawROI = Rect(initialP, finalPoint);
        rectangle(test, drawROI, Scalar(255,255,255), 1);
        imshow("IR Image", test);
    }
    else if(event == EVENT_LBUTTONUP)
    {
        drawing = false;

        if(dragging)
        {
            //imshow("IR Image", test);

            Mat visImg;
            VVC.read(visImg);
            resize(visImg, visImg, imgSize);

            cD.AdjustImage(visImg, xOffset, yOffset, imgSize);

            rectangle(visImg, drawROI, Scalar(255,255,255));
            imshow("Visible Image", visImg);                

            freeze = true;
        }
    }
}

