# MPI Setup Guide for Windows

## Installing Microsoft MPI (MS-MPI)

### Option 1: Download and Install

1. Download MS-MPI from Microsoft:
   - https://www.microsoft.com/en-us/download/details.aspx?id=57467
   - Install both:
     - `msmpisetup.exe` (MS-MPI Runtime)
     - `msmpisdk.msi` (MS-MPI SDK - includes headers and libraries)

2. Default installation paths:
   - Include: `C:\Program Files (x86)\Microsoft SDKs\MPI\Include\`
   - Library: `C:\Program Files (x86)\Microsoft SDKs\MPI\Lib\x64\`

### Option 2: Using vcpkg (Recommended)

```powershell
# Install vcpkg if not already installed
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat

# Install MS-MPI
.\vcpkg install msmpi:x64-windows
```

### Option 3: Using Chocolatey

```powershell
choco install msmpi
```

## Setting Environment Variables

After installation, set these environment variables:

```powershell
# PowerShell (temporary for current session)
$env:MSMPI_INC = "C:\Program Files (x86)\Microsoft SDKs\MPI\Include"
$env:MSMPI_LIB = "C:\Program Files (x86)\Microsoft SDKs\MPI\Lib\x64"

# Or permanently (run as Administrator)
[System.Environment]::SetEnvironmentVariable("MSMPI_INC", "C:\Program Files (x86)\Microsoft SDKs\MPI\Include", "Machine")
[System.Environment]::SetEnvironmentVariable("MSMPI_LIB", "C:\Program Files (x86)\Microsoft SDKs\MPI\Lib\x64", "Machine")
```

## Configuring CMake

### Method 1: Using Environment Variables

If you've set `MSMPI_INC` and `MSMPI_LIB`, CMake will find them automatically.

### Method 2: Command Line

```powershell
cmake .. -DMSMPI_INC="C:/Program Files (x86)/Microsoft SDKs/MPI/Include" -DMSMPI_LIB="C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64"
```

### Method 3: CMake GUI

1. Open CMake GUI
2. Set `MSMPI_INC` to: `C:/Program Files (x86)/Microsoft SDKs/MPI/Include`
3. Set `MSMPI_LIB` to: `C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64`
4. Configure and Generate

## Verifying Installation

After building, you should see:
```
-- Found MS-MPI include: C:/Program Files (x86)/Microsoft SDKs/MPI/Include
-- Found MS-MPI library: C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64/msmpi.lib
-- MPI found: ...
```

## Running MPI Programs

### Single Node (Multiple Processes)

```powershell
# Run with 4 processes
mpiexec -n 4 .\Parallel-Deferred-Renderer.exe

# Or using the full path
"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe" -n 4 .\Parallel-Deferred-Renderer.exe
```

### Multi-Node (if configured)

```powershell
# Create a hostfile
echo localhost > hostfile.txt

# Run across nodes
mpiexec -n 8 -hostfile hostfile.txt .\Parallel-Deferred-Renderer.exe
```

## Troubleshooting

### CMake can't find MPI

1. Check if MS-MPI SDK is installed (not just runtime)
2. Verify environment variables:
   ```powershell
   echo $env:MSMPI_INC
   echo $env:MSMPI_LIB
   ```
3. Manually specify paths in CMake:
   ```powershell
   cmake .. -DMSMPI_INC="<path to Include>" -DMSMPI_LIB="<path to Lib/x64>"
   ```

### Compilation Errors

- Ensure you're using the x64 version of MS-MPI libraries
- Check that `mpi.h` exists in the include directory
- Verify `msmpi.lib` exists in the library directory

### Runtime Errors

- Ensure MS-MPI Runtime is installed
- Check that `mpiexec.exe` is in your PATH or use full path
- Verify you're running the correct architecture (x64)

## Alternative: Use WSL2 with OpenMPI

If MS-MPI causes issues, you can use WSL2:

```bash
# In WSL2
sudo apt-get update
sudo apt-get install libopenmpi-dev openmpi-bin

# Build and run
mpirun -n 4 ./Parallel-Deferred-Renderer
```

