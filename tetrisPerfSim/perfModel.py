'''
Created on Nov 14, 2018

@author: shuangchenli

Simulator:

Performance Model:
The roofline based simulator, takes the sparse data trace input, leverages the shceduler and the reorderEngine,
calculates the intra-core roofline model, inter-core (NoC) roofline model, and the core-mem (SRAM/DRAM w/ reorder) roofline model
also prints status
also have baseline sims

Performance Model for SRAM:
Reading the SRAM with block weight index (multi-bank with effective bank conflicts),
Write the SRAM with the index
'''

# Note: the latency should be in ns. the energy should be in nj

#@liu: maintain this module
from tetrisPerfSim import scheduler, reorderEngine
import numpy as np
import math

#@jilan
def PerfDRAM(memory, dataAmount): # inputs: components.DRAM(), [int] Byte; return (ns, nj)
  # [TODO] @jilan: calc reading/write DRAM, update statics in memory
  # We assume the weight is formated with block and index offline
  # we do not write DRAM - jilan 
  
  # calculate latency and energy
  latency = dataAmount / memory.BW * 1e9 # ns
  energy = dataAmount * 8 * memory.energyPerBit + latency * 1e-9 * memory.leakage * 1e3 #nj
  
  # update the stat in the component.DRAM()
  memory.totalLatency += latency
  memory.numAccess += dataAmount / memory.width
  memory.totalEnergy += energy
  memory.wholeEnergy += energy
  memory.totalReadEnergy += energy
  
  return (latency, energy)

#@ling
def PerfSRAM(memory, address, isREAD): # inputs: components.SRAM(), list[int] address list, [boolean]; return (ns, nj)
  # [TODO] @jilan: calc reading SRAM, update statics in memory

  numBank = memory.numBank
  dataAmount = 0
  for e in address:
    dataAmount += e.size
  numAccess = dataAmount / numBank
  totalConflict = 0

  if(memory.adrHashScheme == 'ideal'):
    # assume maximal bank parallelism zero bank conflict, i.e., no reordering overhead
    # should be the same as PerfBUF (or simply call PerfBUF)

    if isREAD:
      latency = memory.readLatency * numAccess # ns
      energy = memory.readEnergyPerBank * dataAmount + memory.leakage * 1e3 * latency * 1e-9 # nj
    else:
      latency = memory.writeLatency * numAccess
      energy = memory.writeEnergyPerBank * dataAmount + memory.leakage * 1e3 * latency * 1e-9
      # print memory.writeEnergyPerBank * dataAmount, memory.leakage * 1e3 * latency * 1e-9
    # assert(True)

  elif(memory.adrHashScheme == 'modN'): # NOTE THAT SRAM model need to consider multi-bank parallelsim and conflict stuff
    # NOTE THAT we could have a OOO-read/write queue here
    # check memory.reorderBufLen

    numConflictAccess = 0
    # numRegularAccess = 0

    #reshape the address as a vector
    adrOrder = np.reshape(np.asarray(address).T, -1)
    # numRegularAccess = adrOrder.size/numBank
    for i in range(numAccess):
      bankList = []
      numConflict = []
      beginIdx = i * numBank
      for j in range(beginIdx, beginIdx + numBank):
        if adrOrder[j] not in bankList:
          bankList.append(adrOrder[j])
          numConflict.append(1)
        else:
          numConflict[bankList.index(adrOrder[j])] += 1
      numConflictAccess += max(numConflict)
      assert(max(numConflict) < 17)
      #print max(numConflict)
      totalConflict += (sum(numConflict) - len(numConflict))

    if isREAD:
      latency = memory.readLatency * numConflictAccess
      memory.extraLatency += memory.readLatency * (numConflictAccess - numAccess)
      energy = memory.readEnergyPerBank * dataAmount + memory.leakage * 1e3 * latency  * 1e-9
    else:
      latency = memory.writeLatency * numConflictAccess
      memory.extraLatency += memory.readLatency * (numConflictAccess - numAccess)
      energy = memory.writeEnergyPerBank * dataAmount + memory.leakage * 1e3 * latency  * 1e-9
    assert(True)

  else:
    assert(False)


  if isREAD:
    memory.numRead += dataAmount
    memory.totalReadEnergy += energy
    memory.totalReadLatency += latency
  else:
    memory.numWrite += dataAmount
    memory.totalWriteEnergy += energy
    memory.totalWriteLatency += latency


  memory.numBankConflict += totalConflict
  memory.totalEnergy += energy
  memory.wholeEnergy += energy
  memory.totalLatency += latency

  assert(True)

#@jilan  
def PerfBUF(memory, dataAmount, isREAD): # inputs: components.SRAM(), [int] Byte, boolean; return (ns, nj)
  # [TODO] @jilan: calc reading SRAM, update statics in memory
  # NOTE THAT this buffer is modeled simply by BW, assuming maximal bank parallelism and zero bank conflict

  if isREAD:
    # calc latency and energy
    numRead = dataAmount / memory.width
    latency = numRead * memory.readLatency # ns
    energy = numRead * memory.readEnergy + latency * 1e-9 * memory.leakage * 1e3
    # print numRead * memory.readEnergy, latency * 1e-9 * memory.leakage * 1e3, '\n'
    
    # update the stat in the component.SRAM()
    memory.numRead += numRead
    memory.totalReadLatency += latency
    memory.totalReadEnergy += energy
    memory.totalLatency += latency
    memory.totalEnergy += energy
    memory.wholeEnergy += energy
    
  else:
    # calc latency and energy
    numWrite = dataAmount / memory.width
    latency = numWrite * memory.writeLatency # ns
    energy = numWrite * memory.writeEnergy + latency * 1e-9 * memory.leakage * 1e3
    
    # update the stat in the component.SRAM()
    memory.numWrite += numWrite
    memory.totalWriteLatency += latency
    memory.totalWriteEnergy += energy
    memory.totalLatency += latency
    memory.totalEnergy += energy
    memory.wholeEnergy += energy
    
#  assert(True)

#@jilan  
def PerfNOC(noc, dataAmount): # inputs: components.NoC(), [int] Byte; return (ns, nj)
  # [TODO] @jilan: calc reading NoC, update statics in noc
  ener = noc.energyPerByte*dataAmount
  latency = dataAmount/noc.bandwidthTotal*1e9
  noc.dataAmount += dataAmount
  noc.totalEnergy += noc.energyPerByte*dataAmount
  # we assume that the data come from all the PEs
  noc.totalLatency += dataAmount/noc.bandwidthTotal
  noc.wholeEnergy += noc.energyPerByte*dataAmount
  
  assert(noc.totalEnergy == noc.dataAmount*noc.energyPerByte), 'NOC energy should be consistent.'

#@jilan  
def PerfTILE(tile, blocksize, numtask): # inputs: components.Tile(), [int] nxn blocksize, [int] #block to calc; return (ns, nj)
  # [TODO] calc PE computing, update statics in tile
  
  # calc thoughput for a singel blocksize, considering PE utilization
  # e.g., PE with 128x128 MAC with suffer with 1x1 block size
  
  # in current version, we do not consider the utilization and block size
  # print blocksize, tile.nMAC
  # assert(blocksize == tile.nMAC), 'in current version, we do not consider the utilization and block size'
  
  if blocksize == tile.nMAC:
    numCalc = numtask/math.sqrt(blocksize)
    #print numCalc, numtask, math.sqrt(blocksize), '\n'
    tile.avgUtilization = (tile.numBlock*tile.avgUtilization + numCalc)/(tile.numBlock+numCalc)
    tile.numBlock += numCalc
    latency = numtask/math.sqrt(blocksize)*tile.latencyPerMAC #ns
    tile.totalEnergy += (tile.power+tile.leakage) * 1e3*latency*1e-9 #nj
    tile.totalLatency += latency
    tile.wholeEnergy += (tile.power+tile.leakage) * 1e3*latency*1e-9
  else:
    numCalc = numtask/math.sqrt(blocksize)
    tile.avgUtilization = (tile.numBlock*tile.avgUtilization + numCalc)/(tile.numBlock+numCalc)
    tile.numBlock += numCalc
    latency = numtask/math.floor(math.sqrt(blocksize))*tile.latencyPerMAC #ns
    tile.totalEnergy += (tile.power+tile.leakage) * 1e3*latency*1e-9 #nj
    tile.totalLatency += latency
    tile.wholeEnergy += (tile.power+tile.leakage) * 1e3*latency*1e-9
  # dertermined by Tianqi's simulator
  
  # calc all blocks
  # assert(True)

#@jilan  
# def PerfReorder(reorder, totalDataSize): # inputs: components.ReorderDMA(), [int] Byte, boolean; return (ns, nj)
  # [TODO] @jilan: calc reorder, update statics in reorder
  # assert(False), 'we are not using DMA for reordering now'
  
def RoofLine(tetrisArch): # inputs: components.TetrisArch()
  # [TODO] @jilan: min{ total-PE, total-NOC, total-FmapMem, total-ReorderBuf, total-DRAM }, energy add them all
  # update the TetrisArch statics
  # NOTE: should be accumulative
  tetrisArch.totalEnergy += tetrisArch.noc.totalEnergy + tetrisArch.offMem.totalEnergy + tetrisArch.fmapMem.totalEnergy + tetrisArch.tile.totalEnergy*tetrisArch.numTile+tetrisArch.accBuf.totalEnergy
  tetrisArch.totalLatency += max(tetrisArch.noc.totalLatency , tetrisArch.offMem.totalLatency , tetrisArch.fmapMem.totalLatency , tetrisArch.tile.totalLatency , tetrisArch.accBuf.totalLatency)
  tetrisArch.conflictLatency += tetrisArch.fmapMem.extraLatency

  # print abs(tetrisArch.totalEnergy - (tetrisArch.noc.wholeEnergy + tetrisArch.offMem.wholeEnergy + tetrisArch.fmapMem.wholeEnergy + tetrisArch.tile.wholeEnergy*tetrisArch.numTile+tetrisArch.accBuf.wholeEnergy))
  assert(abs(tetrisArch.totalEnergy - (tetrisArch.noc.wholeEnergy + tetrisArch.offMem.wholeEnergy + tetrisArch.fmapMem.wholeEnergy + tetrisArch.tile.wholeEnergy*tetrisArch.numTile+tetrisArch.accBuf.wholeEnergy)) < 0.0001)
  
  assert(True)

#@jilan
def Sim(tetrisArch, layer): # inputs: components.TetrisArch(), traceGen.Layer()
  assert(tetrisArch.noc.totalEnergy == 0)
  assert(tetrisArch.offMem.totalEnergy == 0)
  assert(tetrisArch.fmapMem.totalEnergy == 0)
  assert(tetrisArch.tile.totalEnergy == 0)
  assert(tetrisArch.accBuf.totalEnergy == 0)
  # print layer.numDataBlock
  partition = scheduler.Partition(tetrisArch, layer)
  for partialLayer in partition:
    scheduler.GenFmapRequests(partialLayer)
    
    # calc reading DRAM for weight, update statics in tetrisArch
    totalDataSize = partialLayer.weight['byte']
    PerfDRAM(tetrisArch.offMem, totalDataSize)
    
    # calc reading Fmap from FmapMem, update statics in tetrisArch
    #adr_readFmapMem = reorderEngine.AdrGen(partialLayer.fmapFromFmapMem['dataAdr'], tetrisArch.fmapMem)
    adr_readFmapMem = partialLayer.fmapFromFmapMem['dataAdr']
    # print tetrisArch.fmapMem.adrHashScheme
    PerfSRAM(tetrisArch.fmapMem, adr_readFmapMem, True)
    
    # calc reading Fmap from accBuffer for accumulation, update statics in tetrisArch
    totalDataSize = partialLayer.fmapFromAccBuf['byte']
    PerfBUF(tetrisArch.accBuf, totalDataSize, True)
      
    # calc reading Fmap from PE (Fmap reused by two tiles), update statics in tetrisArch
    #print partialLayer.numBlock
    numtask = (partialLayer.accFmapInNoc['byte'] + partialLayer.fmapToFmapMem['byte'] + partialLayer.fmapToAccBuf['byte'])/partialLayer.numBlock # [TODO] @jilan: figure out num of blocks to compute from partialLayer
    #print layer.numBlockH, layer.numBlockW
    PerfTILE(tetrisArch.tile, layer.blockSizeH * layer.blockSizeW, numtask) 
    
    # calc writing Fmap to FmapMem, update statics in tetrisArch
    # adr_writeFmapMem = reorderEngine.AdrGen(partialLayer.fmapToFmapMem['data'])
    adr_writeFmapMem = partialLayer.fmapToFmapMem['dataAdr']
    PerfSRAM(tetrisArch.fmapMem, adr_writeFmapMem, False)

    # calc writting Fmap from accBuffer for accumulation, update statics in tetrisArch
    totalDataSize = partialLayer.fmapToAccBuf['byte']
    PerfBUF(tetrisArch.accBuf, totalDataSize, False)
    
    # update the reorder engine
    totalDataSize = partialLayer.fmapFromFmapMem['byte'] + partialLayer.fmapToFmapMem['byte']
    #PerfReorder(tetrisArch.reorder, totalDataSize)

    # calc NOC, update statics in tetrisArch
    totalDataSize = partialLayer.dupFmapInNoC['byte'] + partialLayer.fmapFromFmapMem['byte'] + \
                    partialLayer.weight['byte'] + partialLayer.fmapToFmapMem['byte'] + \
                    partialLayer.fmapToAccBuf['byte'] + partialLayer.fmapFromAccBuf['byte']
    PerfNOC(tetrisArch.noc, totalDataSize)
        
    # roofline model, min{ total-PE, total-NOC, total-FmapMem, total-ReorderBuf, total-DRAM }
    RoofLine(tetrisArch)
    tetrisArch.tile.resetStatus()
    tetrisArch.accBuf.resetStatus()
    tetrisArch.offMem.resetStatus()
    tetrisArch.fmapMem.resetStatus()
    tetrisArch.noc.resetStatus()
      
  assert(True)
