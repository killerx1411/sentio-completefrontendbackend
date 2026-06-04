import bcrypt

password = "SecondaryAdmin@123".encode()

hashed = bcrypt.hashpw(password, bcrypt.gensalt())

print(hashed.decode())