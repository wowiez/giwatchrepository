from flask import Flask, request, jsonify
import libvirt
import os

app = Flask(__name__)

def connect_to_hypervisor():
    return libvirt.open('qemu:///system')

@app.route('/')
def index():
    return "Welcome to the VM Cloud Service!"

@app.route('/create_vm', methods=['POST'])
def create_vm():
    vm_name = request.json.get('name')
    vm_memory = request.json.get('memory', 512)  # in MB
    vm_vcpus = request.json.get('vcpus', 1)

    conn = connect_to_hypervisor()
    if conn is None:
        return jsonify({"error": "Failed to connect to the hypervisor."}), 500

    xml_desc = f"""
    <domain type='kvm'>
      <name>{vm_name}</name>
      <memory unit='MiB'>{vm_memory}</memory>
      <vcpu>{vm_vcpus}</vcpu>
      <os>
        <type arch='x86_64' machine='pc-i440fx-2.9'>hvm</type>
      </os>
      <devices>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/{vm_name}.qcow2'/>
          <target dev='vda' bus='virtio'/>
        </disk>
        <interface type='network'>
          <mac address='52:54:00:6b:3c:58'/>
          <source network='default'/>
          <model type='virtio'/>
        </interface>
      </devices>
    </domain>
    """

    try:
        vm = conn.createXML(xml_desc, 0)
        conn.close()
        return jsonify({"success": f"VM {vm_name} created successfully!"})
    except libvirt.libvirtError as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/list_vms', methods=['GET'])
def list_vms():
    conn = connect_to_hypervisor()
    if conn is None:
        return jsonify({"error": "Failed to connect to the hypervisor."}), 500

    vms = []
    for vm_id in conn.listDomainsID():
        vm = conn.lookupByID(vm_id)
        vms.append({"name": vm.name(), "id": vm.ID()})

    conn.close()
    return jsonify({"vms": vms})

@app.route('/delete_vm', methods=['POST'])
def delete_vm():
    vm_name = request.json.get('name')

    conn = connect_to_hypervisor()
    if conn is None:
        return jsonify({"error": "Failed to connect to the hypervisor."}), 500

    try:
        vm = conn.lookupByName(vm_name)
        vm.destroy()
        vm.undefine()
        os.remove(f"/var/lib/libvirt/images/{vm_name}.qcow2")
        conn.close()
        return jsonify({"success": f"VM {vm_name} deleted successfully!"})
    except libvirt.libvirtError as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
