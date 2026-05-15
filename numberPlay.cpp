#include <iostream>
#include <vector>
using namespace std;

// 获取中奖等级函数
int getPrizeLevel(int red_count, bool blue_match) {
    if (red_count == 6) {
        return blue_match ? 1 : 2;
    } else if (red_count == 5) {
        return blue_match ? 3 : 4;
    } else if (red_count == 4) {
        return blue_match ? 4 : 5;
    } else if (red_count == 3) {
        return blue_match ? 5 : 0;
    } else if (blue_match) {
        return 6;
    } else {
        return 0;
    }
}

int main() {
    int n;
    cin >> n; // 读取彩票注数
    
    // 存储所有彩票
    vector<vector<int>> tickets(n, vector<int>(7));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 7; j++) {
            cin >> tickets[i][j];
        }
    }
    
    // 读取中奖号码
    vector<int> win(7);
    for (int i = 0; i < 7; i++) {
        cin >> win[i];
    }
    
    // 拆分中奖号码：前6个是红球，最后1个是蓝球
    vector<int> win_red(win.begin(), win.begin() + 6);
    int win_blue = win[6];
    
    // 处理每一注彩票
    for (int i = 0; i < n; i++) {
        // 拆分当前注
        vector<int> red(tickets[i].begin(), tickets[i].begin() + 6);
        int blue = tickets[i][6];
        
        // 计算红球匹配数量
        int red_count = 0;
        for (int r : red) {
            for (int w : win_red) {
                if (r == w) {
                    red_count++;
                    break;
                }
            }
        }
        
        // 检查蓝球是否匹配
        bool blue_match = (blue == win_blue);
        
        // 获取并输出中奖等级
        cout << getPrizeLevel(red_count, blue_match) << endl;
    }
    
    return 0;
}