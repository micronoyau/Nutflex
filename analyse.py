import matplotlib.pyplot as plt


data = open('results/MAVERICK.mp4_data.txt',"r")

full_data_set=[]

for line in data:
    dic = {}
    l = line.strip().split(" ")
    print(line)
    dic['alpha'] = l[1]
    dic['n_dct'] = l[2]
    dic['encoding_time'] = l[3]
    dic['decoding_time'] = l[4]
    dic['message'] = l[5]
    dic['confidence']=l[6]
    dic['compression']=l[7]
    full_data_set.append(dic)


def plot_correctness():
    X_green = []
    X_red = []
    Y_green = []
    Y_red = []
    for row in full_data_set:
        if row['message']=="314159" and row['compression']=="10":
            X_green.append(row['alpha'])
            Y_green.append(row['n_dct'])
        elif row['compression']=="10":
            X_red.append(row['alpha'])
            Y_red.append(row['n_dct'])
    plt.scatter(X_red,Y_red,color='red')
    plt.scatter(X_green,Y_green,color='green')
    plt.title("Correctness with a compression rate of 0.1")
    plt.show()


def plot_accuracy():
    X_darkgreen = []
    X_green = []
    X_yellow = []
    X_orange = []
    X_red = []
    Y_darkgreen = []
    Y_green = []
    Y_yellow = []
    Y_orange = []
    Y_red = []

    for row in full_data_set:
        if row['compression'] == '10':
            if float(row['confidence']) > 4000:
                X_darkgreen.append(row['alpha'])
                Y_darkgreen.append(row['n_dct'])
            elif float(row['confidence'])  > 2000:
                X_green.append(row['alpha'])
                Y_green.append(row['n_dct'])
            elif float(row['confidence'])  > 800:
                X_yellow.append(row['alpha'])
                Y_yellow.append(row['n_dct'])
            elif float(row['confidence'])  > 10:
                X_orange.append(row['alpha'])
                Y_orange.append(row['n_dct'])
            else :
                X_red.append(row['alpha'])
                Y_red.append(row['n_dct'])
    plt.scatter(X_red,Y_red,color='red')
    plt.scatter(X_orange,Y_orange,color='orange')
    plt.scatter(X_yellow,Y_yellow,color='yellow')
    plt.scatter(X_green,Y_green,color='lime')
    plt.scatter(X_darkgreen,Y_darkgreen,color='darkgreen')
    plt.title("Accuracy with a compression rate of 0.1")
    plt.legend(["Accuracy <= 10","Accuracy in ]10, 800]","Accuracy in ]800, 2000]","Accuracy in ]2000, 4000]","Accuracy >4000"],bbox_to_anchor=(0.5, 0.30))
    plt.show()

def plot_performance():
    x_encode = []
    x_decode = []
    for row in full_data_set:
        x_encode.append(float(row['encoding_time']))
        x_decode.append(float(row['decoding_time']))

    print(f"[Encoding time] : average = {sum(x_encode)/len(x_encode)} | minimum = {min(x_encode)} | maximum = {max(x_encode)}")
    print(f"[Decoding time] : average = {sum(x_decode)/len(x_decode)} | minimum = {min(x_decode)} | maximum = {max(x_decode)}")

def plot_transparence():
    X = [(0.05,30),(0.05,25),(0.05,20),(0.05,15),(0.1,30),(0.1,25),(0.1,20),(0.1,16),(0.1,14),(0.1,10),(0.2,30),(0.2,25),(0.2,20),(0.2,16),(0.2,14),(0.2,10),(0.2,8),(0.2,4),(0.4,25),(0.4,20),(0.4,16),(0.4,14),(0.4,10),(0.4,8),(0.4,4),(0.8,10),(0.8,8),(0.8,4),(0.8,2),(1.5,4),(1.5,2),(2,4),(2,2),(2,1)]
    Y = [3,3,3,2,4,4,3,3,3,2,4,4,4,4,4,3,3,2,4,4,4,4,4,4,3,4,4,4,3,4,4,4,4,4]
    X_red = []
    X_orange = []
    X_yellow = []
    Y_red = []
    Y_orange = []
    Y_yellow = []
    for i in range(len(X)):
        if Y[i] == 2:
            X_yellow.append(X[i][0])
            Y_yellow.append(X[i][1])
        elif Y[i] == 3:
            X_orange.append(X[i][0])
            Y_orange.append(X[i][1])
        else:
            X_red.append(X[i][0])
            Y_red.append(X[i][1])
    plt.scatter(X_red,Y_red,color='red')
    plt.scatter(X_orange,Y_orange,color='orange')
    plt.scatter(X_yellow,Y_yellow,color='yellow')
    plt.title("Transparence levels")
    plt.legend(["a very few artifacts","a large amount of artifcats","too much artifacts"])
    plt.show()

plot_transparence()