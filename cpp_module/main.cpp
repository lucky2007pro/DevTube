#include <iostream>
using namespace std;

int main(int argc, char* argv[]) {
    // Pythondan kelgan sonni o'qiymiz
    if (argc > 1) {
        int number = atoi(argv[1]); // Stringni songa aylantiramiz
        int result = number * number;

        // Natijani ekranga chiqarish (buni Python o'qiydi)
        cout << "C++ Hisobladi: " << number << " ning kvadrati = " << result << endl;
    } else {
        cout << "Xatolik: Son kiritilmadi!" << endl;
    }
    return 0;
}