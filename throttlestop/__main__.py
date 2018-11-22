from json import dumps, loads
from types import SimpleNamespace

from .msr import MSR, parse_MSR_PKG_POWER_LIMIT, parse_MSR_RAPL_POWER_UNIT, build_MSR_PKG_POWER_LIMIT, \
    MSR_PKG_POWER_LIMIT_ADDR, MSR_RAPL_POWER_UNIT_ADDR, MSR_VOLTAGE_ADDR, parse_MSR_UNDERVOLTAGE, build_MSR_VOLTAGE, \
    MSR_VOLTAGE_PLANES
from .tools import NamespaceEncoder


def apply_delta(delta: dict, ns: SimpleNamespace):
    assert isinstance(delta, dict)
    assert isinstance(ns, SimpleNamespace)

    for key, value in delta.items():
        if isinstance(value, dict):
            obj = getattr(ns, key)
            apply_delta(value, obj)
        else:
            setattr(ns, key, value)


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')

    tdp_parser = subparsers.add_parser('tdp')
    tdp_parser.add_argument("tdp", default={}, nargs='?', type=loads)

    voltage_parser = subparsers.add_parser('voltage')
    voltage_parser.add_argument("voltage", default={}, nargs='?', type=loads)

    args = parser.parse_args()
    if not vars(args):
        return

    msr = MSR()

    if hasattr(args, 'tdp'):
        MSR_RAPL_POWER_UNIT = msr.read(MSR_RAPL_POWER_UNIT_ADDR)
        units = parse_MSR_RAPL_POWER_UNIT(MSR_RAPL_POWER_UNIT)

        MSR_PKG_POWER_LIMIT = msr.read(MSR_PKG_POWER_LIMIT_ADDR)
        power_limits = parse_MSR_PKG_POWER_LIMIT(MSR_PKG_POWER_LIMIT, units)

        if args.tdp:
            apply_delta(args.tdp, power_limits)
            result = build_MSR_PKG_POWER_LIMIT(power_limits, units)
            msr.write(MSR_PKG_POWER_LIMIT_ADDR, result)

            power_limits = parse_MSR_PKG_POWER_LIMIT(msr.read(MSR_PKG_POWER_LIMIT_ADDR), units)

        print(dumps(power_limits, indent=4, cls=NamespaceEncoder))

    else:
        outputs = {}
        voltages = args.voltage
        assert voltages.keys() <= MSR_VOLTAGE_PLANES.keys()
        for name, index in MSR_VOLTAGE_PLANES.items():
            if name in args.voltage:
                prompt = build_MSR_VOLTAGE(SimpleNamespace(plane=index, voltage=args.voltage[name]))
                msr.write(MSR_VOLTAGE_ADDR, prompt)
                # Read back result
                prompt = build_MSR_VOLTAGE(SimpleNamespace(plane=index, voltage=None))
                msr.write(MSR_VOLTAGE_ADDR, prompt)

            else:
                prompt = build_MSR_VOLTAGE(SimpleNamespace(plane=index, voltage=None))
                msr.write(MSR_VOLTAGE_ADDR, prompt)

            MSR_VOLTAGE = msr.read(MSR_VOLTAGE_ADDR)
            outputs[name] = parse_MSR_UNDERVOLTAGE(MSR_VOLTAGE)

        print(dumps(outputs, indent=4))


if __name__ == "__main__":
    main()