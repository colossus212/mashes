cmake_minimum_required(VERSION 2.8.3)
project(mashes_measures)

find_package(catkin REQUIRED COMPONENTS
  tf
  rospy
  roscpp
  std_msgs
  cv_bridge
  sensor_msgs
  image_transport
  message_generation
)

# Declare the message files to be built
 add_message_files(FILES
                   MsgGeometry.msg
                   MsgVelocity.msg
                   MsgStatus.msg)
catkin_python_setup()

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)
