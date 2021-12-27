
import yaml

def read_config(file_name):

    info = None
    with open(file_name, 'r') as stream:
        try:
            info = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit()

    return info

if __name__ == "__main__":

    info = read_config('config.yaml')
    print(info)

    for key in info.keys():
        if type(info[key]):
            print("{:16s}: {:s}".format(key, info[key]))