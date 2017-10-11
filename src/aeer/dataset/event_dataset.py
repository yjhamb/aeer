'''
Functions that operate on the dataset
'''
import pandas as pd
import sklearn.model_selection as ms

# global event data
events = None
ny_file_name = "../dataset/rsvp_ny.csv"
sfo_file_name = "../dataset/rsvp_sfo.csv"
dc_file_name = "../dataset/rsvp_dc.csv"
chicago_file_name = "../dataset/rsvp_chicago.csv"

def load_dataset(file_name):
    global events
    print("loading the dataset")
    events = pd.read_csv(file_name)
    
def split_dataset():
    print("performing the training / test split")
    if events is None:
        load_dataset()
    # sort the event data by event time
    events_sorted = events.sort_values(['eventTime'], ascending=True)
    x = events_sorted.drop(['rsvpRating'], axis=1)
    y = events_sorted[['rsvpRating']]
    
    # perform the train-test split
    train_x, test_x, train_y, test_y = ms.train_test_split(x, y, test_size=0.2, random_state=42)
    return train_x, test_x, train_y, test_y

def get_event_count():
    print("computing event count")
    if events is None:
        load_dataset()
    return events.eventId.nunique()
    
def get_users():
    print("returning user list")
    if events is None:
        load_dataset()
    return events.memberId.unique()

def get_user_train_events(user_id):
    print("returning user train events")
    train_x, test_x, train_y, test_y = split_dataset()
    return train_x.eventId[train_x.memberId == user_id].unique()

def get_user_test_events(user_id):
    print("returning user test events")
    train_x, test_x, train_y, test_y = split_dataset()
    return test_x.eventId.unique()
       
def main():
    print("main method")
    users = get_users()
    print("Train Events Count:", len(get_user_train_events(users[0])))
    print("Test Events Count:", len(get_user_test_events(users[0])))

if __name__ == '__main__':
    main()