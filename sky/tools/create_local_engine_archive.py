#!/usr/bin/env python3
#
# Copyright 2013 The Flutter Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Generates and zip the ios flutter framework including the architecture
# dependent snapshot.

import argparse
import os
import platform
import shutil
import subprocess
import sys

from create_xcframework import create_xcframework  # pylint: disable=import-error

ARCH_SUBPATH = 'mac-arm64' if platform.processor() == 'arm' else 'mac-x64'
DSYMUTIL = os.path.join(
    os.path.dirname(__file__), '..', '..', 'buildtools', ARCH_SUBPATH, 'clang', 'bin', 'dsymutil'
)

buildroot_dir = os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', '..', '..'))


def main():
  parser = argparse.ArgumentParser(
      description=(
          'Creates Flutter.framework, Flutter.xcframework and '
          'copies architecture-dependent gen_snapshot binaries to output dir'
      )
  )

  parser.add_argument('--dst', type=str, required=True)
  parser.add_argument('--clang-dir', type=str, default='clang_x64')
  parser.add_argument('--arm64-out-dir', type=str, required=True)
  parser.add_argument('--simulator-x64-out-dir', type=str, required=True)
  parser.add_argument('--simulator-arm64-out-dir', type=str, required=False)
  parser.add_argument('--host-out-dir', type=str, required=True)
  parser.add_argument('--host-arm64-out-dir', type=str, required=False)
  parser.add_argument('--strip', action='store_true', default=False)
  parser.add_argument('--dsym', action='store_true', default=False)

  args = parser.parse_args()

  dst = (args.dst if os.path.isabs(args.dst) else os.path.join(buildroot_dir, args.dst))

  arm64_out_dir = (
      args.arm64_out_dir
      if os.path.isabs(args.arm64_out_dir) else os.path.join(buildroot_dir, args.arm64_out_dir)
  )

  host_out_dir = (
      args.host_out_dir
      if os.path.isabs(args.host_out_dir) else os.path.join(buildroot_dir, args.host_out_dir)
  )

  host_arm64_out_dir = None
  if args.host_arm64_out_dir:
    host_arm64_out_dir = (
        args.host_arm64_out_dir if os.path.isabs(args.host_arm64_out_dir) else
        os.path.join(buildroot_dir, args.host_arm64_out_dir)
    )

  simulator_x64_out_dir = None
  if args.simulator_x64_out_dir:
    simulator_x64_out_dir = (
        args.simulator_x64_out_dir if os.path.isabs(args.simulator_x64_out_dir) else
        os.path.join(buildroot_dir, args.simulator_x64_out_dir)
    )

  simulator_arm64_out_dir = None
  if args.simulator_arm64_out_dir:
    simulator_arm64_out_dir = (
        args.simulator_arm64_out_dir if os.path.isabs(args.simulator_arm64_out_dir) else
        os.path.join(buildroot_dir, args.simulator_arm64_out_dir)
    )

  copy_runtime(dst, arm64_out_dir, 'runtime')
  copy_runtime(dst, host_out_dir, 'host')
  copy_runtime(dst, host_arm64_out_dir, 'host_arm64')
  copy_runtime(dst, simulator_x64_out_dir, 'simulator_x64')
  copy_runtime(dst, simulator_arm64_out_dir, 'simulator_arm64')

  extension_safe_dst = os.path.join(dst, 'extension_safe')
  create_extension_safe_framework(
      args, extension_safe_dst, '%s_extension_safe' % arm64_out_dir,
      '%s_extension_safe' % simulator_x64_out_dir, '%s_extension_safe' % simulator_arm64_out_dir
  )

  alt_extension_safe_dst = os.path.join(dst, 'alt_extension_safe')
  create_alt_extension_safe_framework(
      args, alt_extension_safe_dst, '%s_alt_extension_safe' % arm64_out_dir,
      '%s_alt_extension_safe' % simulator_x64_out_dir, '%s_alt_extension_safe' % simulator_arm64_out_dir
  )

  zip_archive(dst)
  return 0

def copy_runtime(dst, source_out_dir, runtime_name):
  runtime_out_dir = os.path.join(dst, runtime_name)
  if not source_out_dir is None and os.path.isdir(source_out_dir):
    shutil.rmtree(runtime_out_dir, True)
    shutil.copytree(source_out_dir, runtime_out_dir)

  return runtime_out_dir

def create_extension_safe_framework( # pylint: disable=too-many-arguments
    args, dst, arm64_out_dir, simulator_x64_out_dir, simulator_arm64_out_dir
):
  framework = os.path.join(dst, 'Flutter.framework')
  simulator_framework = os.path.join(dst, 'sim', 'Flutter.framework')
  arm64_framework = os.path.join(arm64_out_dir, 'Flutter.framework')
  simulator_x64_framework = os.path.join(simulator_x64_out_dir, 'Flutter.framework')
  simulator_arm64_framework = os.path.join(simulator_arm64_out_dir, 'Flutter.framework')

  if not os.path.isdir(arm64_framework):
    print('Cannot find extension safe iOS arm64 Framework at %s' % arm64_framework)
    return 1

  if not os.path.isdir(simulator_x64_framework):
    print('Cannot find extension safe iOS x64 simulator Framework at %s' % simulator_x64_framework)
    return 1

  create_framework(
      args, dst, framework, arm64_framework, simulator_framework, simulator_x64_framework,
      simulator_arm64_framework
  )
  return 0

def create_alt_extension_safe_framework( # pylint: disable=too-many-arguments
    args, dst, arm64_out_dir, simulator_x64_out_dir, simulator_arm64_out_dir
):
  framework = os.path.join(dst, 'FlutterExtension.framework')
  simulator_framework = os.path.join(dst, 'sim', 'FlutterExtension.framework')
  arm64_framework = os.path.join(arm64_out_dir, 'FlutterExtension.framework')
  simulator_x64_framework = os.path.join(simulator_x64_out_dir, 'FlutterExtension.framework')
  simulator_arm64_framework = os.path.join(simulator_arm64_out_dir, 'FlutterExtension.framework')

  if not os.path.isdir(arm64_framework):
    print('Cannot find alt extension safe iOS arm64 Framework at %s' % arm64_framework)
    return 1

  if not os.path.isdir(simulator_x64_framework):
    print('Cannot find alt extension safe iOS x64 simulator Framework at %s' % simulator_x64_framework)
    return 1

  create_framework(
      args, dst, framework, arm64_framework, simulator_framework, simulator_x64_framework,
      simulator_arm64_framework, framework_name='FlutterExtension'
  )
  return 0

def create_framework(  # pylint: disable=too-many-arguments
    args, dst, framework, arm64_framework, simulator_framework,
    simulator_x64_framework, simulator_arm64_framework, framework_name='Flutter'
):
  arm64_dylib = os.path.join(arm64_framework, framework_name)
  simulator_x64_dylib = os.path.join(simulator_x64_framework, framework_name)
  simulator_arm64_dylib = os.path.join(simulator_arm64_framework, framework_name)
  if not os.path.isfile(arm64_dylib):
    print('Cannot find iOS arm64 dylib at %s' % arm64_dylib)
    return 1

  if not os.path.isfile(simulator_x64_dylib):
    print('Cannot find iOS simulator dylib at %s' % simulator_x64_dylib)
    return 1

  # Compute dsym output paths, if enabled.
  framework_dsym = None
  simulator_dsym = None
  if args.dsym:
    framework_dsym = framework + '.dSYM'
    simulator_dsym = simulator_framework + '.dSYM'

  # Emit the framework for physical devices.
  shutil.rmtree(framework, True)
  shutil.copytree(arm64_framework, framework)
  framework_binary = os.path.join(framework, framework_name)
  process_framework(args, dst, framework_binary, framework_dsym, framework_name)

  # Emit the framework for simulators.
  if args.simulator_arm64_out_dir is not None:
    shutil.rmtree(simulator_framework, True)
    shutil.copytree(simulator_arm64_framework, simulator_framework)

    simulator_framework_binary = os.path.join(simulator_framework, framework_name)

    # Create the arm64/x64 simulator fat framework.
    subprocess.check_call([
        'lipo', simulator_x64_dylib, simulator_arm64_dylib, '-create', '-output',
        simulator_framework_binary
    ])
    process_framework(args, dst, simulator_framework_binary, simulator_dsym, framework_name)
  else:
    simulator_framework = simulator_x64_framework

  # Create XCFramework from the arm-only fat framework and the arm64/x64
  # simulator frameworks, or just the x64 simulator framework if only that one
  # exists.
  xcframeworks = [simulator_framework, framework]
  dsyms = [simulator_dsym, framework_dsym] if args.dsym else None
  create_xcframework(location=dst, name=framework_name, frameworks=xcframeworks, dsyms=dsyms)

  # Add the x64 simulator into the fat framework.
  subprocess.check_call([
      'lipo', arm64_dylib, simulator_x64_dylib, '-create', '-output', framework_binary
  ])

  process_framework(args, dst, framework_binary, framework_dsym, framework_name)
  return 0


def embed_codesign_configuration(config_path, contents):
  with open(config_path, 'w') as file:
    file.write('\n'.join(contents) + '\n')


def zip_archive(dst):
  subprocess.check_call([
      'zip',
      '-r',
      'artifacts.zip',
      'runtime',
      'host',
      'host_arm64',
      'simulator_x64',
      'simulator_arm64',
      'extension_safe/Flutter.xcframework',
      'alt_extension_safe/FlutterExtension.xcframework',
  ],
                        cwd=dst)

  # Generate Flutter.dSYM.zip for manual symbolification.
  #
  # Historically, the framework dSYM was named Flutter.dSYM, so in order to
  # remain backward-compatible with existing instructions in docs/Crashes.md
  # and existing tooling such as dart-lang/dart_ci, we rename back to that name
  #
  # TODO(cbracken): remove these archives and the upload steps once we bundle
  # dSYMs in app archives. https://github.com/flutter/flutter/issues/116493
  extension_safe_dsym = os.path.join(dst, 'extension_safe', 'Flutter.framework.dSYM')
  if os.path.exists(extension_safe_dsym):
    renamed_dsym = extension_safe_dsym.replace('Flutter.framework.dSYM', 'Flutter.dSYM')
    os.rename(extension_safe_dsym, renamed_dsym)
    subprocess.check_call(['zip', '-r', 'extension_safe_Flutter.dSYM.zip', 'extension_safe/Flutter.dSYM'], cwd=dst)

  alt_extension_safe_dsym = os.path.join(dst, 'alt_extension_safe', 'FlutterExtension.framework.dSYM')
  if os.path.exists(alt_extension_safe_dsym):
    renamed_dsym = alt_extension_safe_dsym.replace('FlutterExtension.framework.dSYM', 'FlutterExtension.dSYM')
    os.rename(alt_extension_safe_dsym, renamed_dsym)
    subprocess.check_call(['zip', '-r', 'alt_extension_safe_FlutterExtension.dSYM.zip', 'alt_extension_safe/FlutterExtension.dSYM'], cwd=dst)  


def process_framework(args, dst, framework_binary, dsym, framework_name='Flutter'):
  if dsym:
    subprocess.check_call([DSYMUTIL, '-o', dsym, framework_binary])

  if args.strip:
    # copy unstripped
    unstripped_out = os.path.join(dst, '%s.unstripped' % framework_name)
    shutil.copyfile(framework_binary, unstripped_out)
    subprocess.check_call(['strip', '-x', '-S', framework_binary])

if __name__ == '__main__':
  sys.exit(main())
