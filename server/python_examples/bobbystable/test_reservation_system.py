from reservation_system import (
    create_reservation,
    get_reservation,
    update_reservation,
    cancel_reservation,
    move_reservation
)

def test_reservation_system():
    # Test create reservation
    create_data = {
        "name": "John Doe",
        "party_size": 4,
        "date": "2024-12-25",
        "time": "18:30",
        "phone_number": "+19185551234"
    }
    print(create_reservation(create_data))

    # Test get reservation
    get_data = {"phone_number": "+19185551234"}
    print(get_reservation(get_data))

    # Test update reservation
    update_data = {
        "phone_number": "+19185551234",
        "party_size": 6
    }
    print(update_reservation(update_data))

    # Test move reservation
    move_data = {
        "phone_number": "+19185551234",
        "new_date": "2024-12-26",
        "new_time": "19:00"
    }
    print(move_reservation(move_data))

    # Test cancel reservation
    cancel_data = {"phone_number": "+19185551234"}
    print(cancel_reservation(cancel_data))

if __name__ == "__main__":
    test_reservation_system() 