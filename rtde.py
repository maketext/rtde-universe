import struct
import socket

class Command:
    RTDE_REQUEST_PROTOCOL_VERSION = 86  # ascii V
    RTDE_GET_URCONTROL_VERSION = 118  # ascii v
    RTDE_TEXT_MESSAGE = 77  # ascii M
    RTDE_DATA_PACKAGE = 85  # ascii U
    RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS = 79  # ascii O
    RTDE_CONTROL_PACKAGE_SETUP_INPUTS = 73  # ascii I
    RTDE_CONTROL_PACKAGE_START = 83  # ascii S
    RTDE_CONTROL_PACKAGE_PAUSE = 80  # ascii P
RTDE_PROTOCOL_VERSION_1 = 1
RTDE_PROTOCOL_VERSION_2 = 2
CurrentRTDEVersion = None


"""
buf = b'\x00\x05V\x00\x01'
(size, command) = struct.unpack_from(">HB", buf) # 아무리 데이터가 길어도 첫 3바이트만 파싱한다.
print(size, command)
"""


def unpack_protocol_version_package(body):
    if len(body) != 1:
        return None
    result = struct.unpack_from(">B", body)[0]
    return result

def unpack_urcontrol_version_package(body):
    if len(body) != 16:
        return None
    major, minor, bugfix, build = struct.unpack_from(">IIII", body)
    return f"{major}, {minor}, {bugfix} build({build})"

def unpack_text_message(body):
    if len(body) < 1:
        return None
    if CurrentRTDEVersion == RTDE_PROTOCOL_VERSION_1:
        offset = 0
        level = struct.unpack_from(">B", body, offset)[0]
        offset = offset + 1
        message = str(body[offset:])
        # message, level
    else:
        offset = 0
        msg_length = struct.unpack_from(">B", body, offset)[0]
        offset = offset + 1
        message = str(body[offset: offset + msg_length])
        offset = offset + msg_length

        src_length = struct.unpack_from(">B", body, offset)[0]
        offset = offset + 1
        source = str(body[offset: offset + src_length])
        offset = offset + src_length
        level = struct.unpack_from(">B", body, offset)[0]
        # message, source, level

    EXCEPTION_MESSAGE = 0
    ERROR_MESSAGE = 1
    WARNING_MESSAGE = 2
    INFO_MESSAGE = 3
    source = ""
    if level == EXCEPTION_MESSAGE:
        source = "EXCEPTION_MESSAGE"
    elif level == ERROR_MESSAGE:
        source = "ERROR_MESSAGE"
    elif level == WARNING_MESSAGE:
        source = "WARNING_MESSAGE"
    elif level == INFO_MESSAGE:
        source = "INFO_MESSAGE"
    return source + ": " + message


class DataConfig:

    def unpack_setup_inout_package(self, body):
        if len(body) < 1:
            return None
        self.id = struct.unpack_from(">B", body)[0]
        self.types = body.decode("utf-8")[1:].split(",")
        self.fmt = ">B"
        for i in self.types:
            if i == "INT32":
                self.fmt += "i"
            elif i == "UINT32":
                self.fmt += "I"
            elif i == "VECTOR6D":
                self.fmt += "d" * 6
            elif i == "VECTOR3D":
                self.fmt += "d" * 3
            elif i == "VECTOR6INT32":
                self.fmt += "i" * 6
            elif i == "VECTOR6UINT32":
                self.fmt += "I" * 6
            elif i == "DOUBLE":
                self.fmt += "d"
            elif i == "UINT64":
                self.fmt += "Q"
            elif i == "UINT8":
                self.fmt += "B"
            elif i == "BOOL":
                self.fmt += "?"
            elif i == "IN_USE":
                return "An input parameter is already in use."
            else:
                return "Unknown data type: " + i
        return "An input parameter is set."

    def pack(self, state):
        l = state.pack(self.names, self.types)
        return struct.pack(self.fmt, *l)

    def unpack(self, data):
        pass
        """
        li = struct.unpack_from(self.fmt, data)

        if len(self.names) != len(types):
            raise ValueError("List sizes are not identical.")
        offset = 0
        recipe_id = data[0]
        self.values = []
        for i in range(len(self.names)):
            self.values.append(unpack_field(data[1:], offset, types[i]))
            offset += get_item_size(types[i])
        """

class CurrentContext:
    def __init__(self):
        pass
    def setInDataConfig(self, dataInConfig):
        self.dataInConfig = dataInConfig

    def setOutDataConfig(self, dataOutConfig):
        self.dataOutConfig = dataOutConfig


def unpack_start_package(body):
    if len(body) < 1:
        return None
    return struct.unpack_from(">B", body)[0]

def unpack_pause_package(body):
    if len(body) < 1:
        return None
    return struct.unpack_from(">B", body)[0]

outputContext = CurrentContext()

class TCPClient:
    def __init__(self):
        pass
    def connect(self):
        self.hostname = "192.168.0.61"
        self.port = 30004

        self.__buf = b""  # buffer data in binary format
        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.__sock.settimeout(5000)
            self.__skipped_package_count = 0
            self.__sock.connect((self.hostname, self.port))
        except (socket.timeout, socket.error):
            self.__sock = None
            raise

        cmd = Command.RTDE_REQUEST_PROTOCOL_VERSION
        payload = struct.pack(">H", RTDE_PROTOCOL_VERSION_2)
        success = self.sendall(cmd, payload)
        if success:
            self.__protocolVersion = RTDE_PROTOCOL_VERSION_2
        return success

    def disconnect(self):
        if self.__sock:
            self.__sock.close()
            self.__sock = None

    def sendall(self, command, payload=b""):
        # > 빅엔디안
        # H unsinged short (2 bytes integer)
        # B unsigned char (1 ascii character)
        fmt = ">HB"
        size = struct.calcsize(fmt) + len(payload)
        buf = struct.pack(fmt, size, command) + payload
        print("SEND: ", buf)

        self.__sock.sendall(buf)
        return True

    def recv(self, context : CurrentContext):
        global CurrentRTDEVersion
        buf = self.__sock.recv(256)
        if len(buf) < 3:
            return
        (size, cmd) = struct.unpack_from(">HB", buf)
        if len(buf) >= size:
            body = buf[3:size]
            result = ""
            if cmd == Command.RTDE_REQUEST_PROTOCOL_VERSION:
                CurrentRTDEVersion = unpack_protocol_version_package(body)
                result = f"RTDE_REQUEST_PROTOCOL_VERSION={CurrentRTDEVersion}"
            elif cmd == Command.RTDE_GET_URCONTROL_VERSION:
                CurrentRTDEVersion = unpack_urcontrol_version_package(body)
                result = f"RTDE_GET_URCONTROL_VERSION={CurrentRTDEVersion}"
            elif cmd == Command.RTDE_TEXT_MESSAGE:
                result = unpack_text_message(body)
            elif cmd == Command.RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS:
                data = DataConfig()
                result = data.unpack_setup_inout_package(body)
                context.setOutDataConfig(data)
            elif cmd == Command.RTDE_CONTROL_PACKAGE_SETUP_INPUTS:
                data = DataConfig()
                result = data.unpack_setup_inout_package(body)
                context.setInDataConfig(data)
            elif cmd == Command.RTDE_CONTROL_PACKAGE_START:
                unpack_start_package(body)
            elif cmd == Command.RTDE_CONTROL_PACKAGE_PAUSE:
                unpack_pause_package(body)
            elif cmd == Command.RTDE_DATA_PACKAGE:
                result = context.dataOutConfig.unpack(body)
        print("RECV: " + result)

        return result

tcp = TCPClient()


def sendAndReceive(command, payload):
    pass

def send_input_setup(context : CurrentContext, variables : list):
    cmd = Command.RTDE_CONTROL_PACKAGE_SETUP_INPUTS
    payload = bytearray(",".join(variables), "utf-8")
    print(payload)
    tcp.sendall(cmd, payload)
    tcp.recv(context)

def send_output_setup(context, variables, types, frequency=250): #125
    def __list_equals(l1, l2):
        if len(l1) != len(l2):
            return False
        for i in range(len((l1))):
            if l1[i] != l2[i]:
                return False
        return True
    cmd = Command.RTDE_CONTROL_PACKAGE_SETUP_OUTPUTS
    payload = struct.pack(">d", frequency)
    payload = payload + (",".join(variables).encode("utf-8"))
    tcp.sendall(cmd, payload)
    tcp.recv(context)
    if len(types) != 0 and not __list_equals(context.dataOutConfig.types, types):
        return "Data type inconsistency for output setup: " + str(types) + " - " + str(context.dataOutConfig.types)
    #context.dataOutConfig.setOutNames(variables)

class Data():
    def __init__(self):
        self.id = None
        self.fmt = ''

    def pack(self, values):
        return struct.pack(self.fmt, self.id, *values)

    def unpack(self, data):
        li = struct.unpack_from(self.fmt, data)
        print(li)

    def unpack_recipe(self, buf):
        self.id = struct.unpack_from(">B", buf)[0]
        self.types = buf.decode("utf-8")[1:].split(",")
        self.fmt = ">B"
        for i in self.types:
            if i == "INT32":
                self.fmt += "i"
            elif i == "UINT32":
                self.fmt += "I"
            elif i == "VECTOR6D":
                self.fmt += "d" * 6
            elif i == "VECTOR3D":
                self.fmt += "d" * 3
            elif i == "VECTOR3INT32":
                self.fmt += "i" * 3
            elif i == "VECTOR6INT32":
                self.fmt += "i" * 6
            elif i == "VECTOR6UINT32":
                self.fmt += "I" * 6
            elif i == "DOUBLE":
                self.fmt += "d"
            elif i == "UINT64":
                self.fmt += "Q"
            elif i == "UINT8":
                self.fmt += "B"
            elif i == "BOOL":
                self.fmt += "?"
            elif i == "IN_USE":
                raise ValueError("An input parameter is already in use.")
            else:
                raise ValueError("Unknown data type: " + i)
        return self.id, self.types, self.fmt


context1 = CurrentContext()
context2 = CurrentContext()

def init():
    tcp.connect()

    tcp.sendall(Command.RTDE_GET_URCONTROL_VERSION, b"")
    tcp.recv(context1)

    tcp.sendall(Command.RTDE_CONTROL_PACKAGE_START, b"")
    tcp.recv(context1)

    send_input_setup(context1, ['input_int_register_0', 'input_int_register_1', 'input_int_register_2'])
    send_input_setup(context2, ['input_double_register_0', 'input_double_register_1', 'input_double_register_2'])
    send_output_setup(outputContext, ['target_q', 'target_qd', 'output_int_register_0'], ['VECTOR6D', 'VECTOR6D', 'INT32'])

def sendData(context : CurrentContext, payload : list, fmt : bytes):
    data = Data()
    data.unpack_recipe(struct.pack(">B", context.dataInConfig.id) + fmt) #id + fmt
    packed = data.pack(payload)
    data.unpack(packed)
    tcp.sendall(Command.RTDE_DATA_PACKAGE, packed)

def setInt3(data): #[1, 2, 3]
    sendData(context1, data, b"VECTOR3INT32")

def setDouble3(data): #[.1, .2, .3]
    sendData(context2, data, b"VECTOR3D")

def pause():
    tcp.sendall(Command.RTDE_CONTROL_PACKAGE_PAUSE, b"")
    tcp.recv(context1)

def stop():
    tcp.disconnect()