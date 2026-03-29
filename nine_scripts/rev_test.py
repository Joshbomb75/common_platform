import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time

rclpy.init()
node = Node('rev_test')
pub = node.create_publisher(Twist, '/cmd_vel', 10)
time.sleep(1)

def spin_wheel(side, seconds):
    v = 0.3
    tw = 0.142
    msg = Twist()
    if side == 'left':
        msg.linear.x = v / 2.0
        msg.angular.z = -(v / tw)
    else:
        msg.linear.x = v / 2.0
        msg.angular.z = (v / tw)
    end = time.time() + seconds
    while time.time() < end:
        pub.publish(msg)
        time.sleep(0.05)
    stop = Twist()
    for _ in range(5):
        pub.publish(stop)
        time.sleep(0.05)

input("Mark a spoke on the LEFT wheel, press Enter to spin 5s...")
spin_wheel('left', 5)
left = input("LEFT done. How many full revolutions? ")
time.sleep(1)
input("Mark a spoke on the RIGHT wheel, press Enter to spin 5s...")
spin_wheel('right', 5)
right = input("RIGHT done. How many full revolutions? ")
node.destroy_node()
rclpy.shutdown()
print(f"Left: {left} revs | Right: {right} revs")
