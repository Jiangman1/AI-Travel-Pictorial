import os

# 项目根路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_file_path(relative_path):
    return os.path.join(root_dir, relative_path)


if __name__ == '__main__':
    print(get_file_path('data/aa.txt'))