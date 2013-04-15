#!/usr/bin/env python
# pmx  Copyright Notice
# ============================
#
# The pmx source code is copyrighted, but you can freely use and
# copy it as long as you don't change or remove any of the copyright
# notices.
#
# ----------------------------------------------------------------------
# pmx is Copyright (C) 2006-2013 by Daniel Seeliger
#
#                        All Rights Reserved
#
# Permission to use, copy, modify, distribute, and distribute modified
# versions of this software and its documentation for any purpose and
# without fee is hereby granted, provided that the above copyright
# notice appear in all copies and that both the copyright notice and
# this permission notice appear in supporting documentation, and that
# the name of Daniel Seeliger not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# DANIEL SEELIGER DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS.  IN NO EVENT SHALL DANIEL SEELIGER BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# ----------------------------------------------------------------------

import sys, os, copy
from pmx import *
from pmx.forcefield2 import Topology
from pmx.mutdb import read_mtp_entry
from pmx.parser import kickOutComments

_perturbed_nucleotides = ['DAT','DAC','DAG','DCT','DCG','DCA',
                          'DTA','DTG','DTC','DGA','DGC','DGT',
                          'RAU','RAC','RAG','RCU','RCG','RCA',
                          'RUA','RUG','RUC','RGA','RGC','RGU',
                          ]


def check_case(atoms):
    A = ''
    B = ''
    for a in atoms:
        if a.atomtype.startswith('DUM'): A += 'D'
        else: A += 'A'
        if a.atomtypeB is not None:
            if a.atomtypeB.startswith('DUM'): B += 'D'
            else: B += 'A'
        else: B += 'A'
    return A, B

def dump_atoms_and_exit( msg, atoms ):
    print >>sys.stderr, 'err_> ', msg
    print >>sys.stderr, 'err_>  name      resname      atomtype       atomtypeB       bondtype       bondtypeB'
    for atom in atoms:
        print >>sys.stderr, atom.name, atom.resname, atom.atomtype, atom.atomtypeB, atom.type, atom.typeB
    print >>sys.stderr, 'err_> Exiting'
    sys.exit(1)
    
def atoms_morphe(atoms):
    for atom in atoms:
        if atom.atomtypeB is not None and (atom.q!=atom.qB or atom.m != atom.mB): return True
    return False

def types_morphe(atoms):
    for atom in atoms:
        if atom.atomtypeB is not None and atom.atomtype != atom.atomtypeB: return True
    return False


def find_bonded_entries( topol ):
    count = 0
    for b in topol.bonds:
        a1,a2,func = b
        A, B = check_case([a1,a2])
        if a1.atomtypeB is not None or a2.atomtypeB is not None:
            count+=1
            error_occured = False
            astate = None
            bstate = None
            if A == 'AA' and B == 'AA': # we need A and B state
                astate = topol.BondedParams.get_bond_param(a1.type,a2.type)
                bstate = topol.BondedParams.get_bond_param(a1.typeB,a2.typeB)
                b.extend([astate,bstate])
            elif 'D' in A and B=='AA':
                bstate = topol.BondedParams.get_bond_param(a1.typeB,a2.typeB)
                astate = bstate
                b.extend([astate,bstate])
            elif 'D' in B and A=='AA':
                astate = topol.BondedParams.get_bond_param(a1.type,a2.type)
                bstate = astate
                b.extend([astate,bstate])
            # catch errors
            elif 'D' in B and 'D' in A:
                print 'Error: fake bond %s-%s (%s-%s -> %s-%s)' % (a1.name,a2.name,a1.atomtype,a2.atomtype, a1.atomtypeB,a2.atomtypeB)
                sys.exit(1)
            if astate == None:
                print 'Error A: No bond entry found for astate %s-%s (%s-%s -> %s-%s)' % (a1.name,a2.name,a1.atomtype,a2.atomtype, a1.type,a2.type)
                print 'Resi = %s' % a1.resname
                error_occured = True
                print A, B

            if bstate == None:
                print 'Error B: No bond entry found for bstate %s-%s (%s-%s -> %s-%s)' % (a1.name,a2.name,a1.atomtypeB,a2.atomtypeB, a1.typeB,a2.typeB)
                error_occured = True
                print A, B
            if error_occured:
                sys.exit(1)
    print 'log_> Making bonds for state B -> %d bonds with perturbed atoms' % count

def find_angle_entries(topol):
    count = 0
    for a in topol.angles:
        a1,a2,a3,func = a
        astate = None
        bstate = None
        if a1.atomtypeB is not None or \
           a2.atomtypeB is not None or \
           a3.atomtypeB is not None:
            A, B = check_case([a1,a2,a3])
            count+=1
            if 'D' in A and 'D' in B: # fake angle
                astate = [1,0,0]
                bstate = [1,0,0]
                a.extend([astate,bstate])
            elif A == 'AAA' and 'D' in B: # take astate
                astate = topol.BondedParams.get_angle_param(a1.type,a2.type,a3.type)
                bstate = astate
                a.extend([astate,bstate])
            elif 'D' in A and B == 'AAA': # take bstate
                bstate = topol.BondedParams.get_angle_param(a1.typeB,a2.typeB,a3.typeB)
                astate = bstate
                a.extend([astate,bstate])
            elif A == 'AAA' and B == 'AAA':
                if a1.atomtypeB != a1.atomtype or \
                   a2.atomtypeB != a2.atomtype or \
                   a3.atomtypeB != a3.atomtype:
                    astate = topol.BondedParams.get_angle_param(a1.type,a2.type,a3.type)
                    bstate = topol.BondedParams.get_angle_param(a1.typeB,a2.typeB,a3.typeB)
                    a.extend([astate, bstate])
#		    print '%s %s %s' % (a1.name, a2.name, a3.name)
                else:
                    astate = topol.BondedParams.get_angle_param(a1.type,a2.type,a3.type)
                    bstate = astate
                    a.extend([astate, bstate])
            if astate is None:
                dump_atoms_and_exit( "No angle entry (state A)", [a1,a2,a3] )
            if bstate is None:
                dump_atoms_and_exit( "No angle entry (state B)", [a1,a2,a3] )

    print 'log_> Making angles for state B -> %d angles with perturbed atoms' % count


def check_dih_ILDN( topol, rlist, rdic, a1, a2, a3, a4 ):
    counter = 0
    for r in rlist:
	if( r.id == a2.resnr ):
	    idx = r.id - 1
            dih = rdic[r.resname][3]
            for d in dih:
		if( counter == 1):
		    break
                al = []
                for name in d[:4]:
                    atom = r.fetch(name)[0]
                    al.append(atom)
                        
                if (a1.id == al[0].id and \
                   a2.id == al[1].id and \
                   a3.id == al[2].id and \
                   a4.id == al[3].id) or \
                   (a1.id == al[3].id and \
                   a2.id == al[2].id and \
                   a3.id == al[1].id and \
                   a4.id == al[0].id):
		    if( ('torsion' in d[4]) and ('torsion' in d[5]) ):
		        print 'torsion %s %s' % (d[4],d[5])
			counter = 42
			break
		    elif( ('torsion' in d[4]) and ('undefined' in d[5]) ):
                        print 'torsion_undef %s %s' % (d[4],d[5])
                        counter = 2
                        break
                    elif( ('undefined' in d[4]) and ('torsion' in d[5]) ):
                        print 'torsion_undef %s %s' % (d[4],d[5])
                        counter = 3
                        break
		    elif( 'undefined' in d[4] ):
			print 'undef %s' %d[4]
			counter = 1
			break
    return counter


def is_dih_encountered(visited_dih, d, encountered):
    for dih in visited_dih:
	if( dih[0].id==d[0].id and dih[1].id==d[1].id and dih[2].id==d[2].id and dih[3].id==d[3].id ):
	    encountered = 1
    return encountered


def find_dihedral_entries( topol, rlist, rdic, dih_predef_default ):
    count = 0
    nfake = 0
    dih9 = [] # here I will accumulate multiple entries of type 9 dihedrals
    visited_dih = [] # need to store already visited angles to avoid multiple re-definitions

    for d in topol.dihedrals:
        if len(d) >= 6:

	    # only consider the dihedral, if it has not been encountered so far
	    encountered = 0
	    encountered = is_dih_encountered(visited_dih, d, encountered)
	    encountered = is_dih_encountered(dih_predef_default, d, encountered)
	    if(encountered == 1):
		continue

	    if(len(d) == 6):
                a1,a2,a3,a4, func, val = d
	    else:
                a1,a2,a3,a4, func, val, rest = d
		
            backup_d = d[:6]
            
            if atoms_morphe([a1,a2,a3,a4]):
                A,B= check_case(d[:4])
                if A!='AAAA' and B!='AAAA':
                    nfake+=1
                    # these are fake dihedrals
                    d[5] = 'NULL'
                    d.append('NULL')
                else:
                    count +=1
		    astate = []
		    bstate = []
                    if A == 'AAAA' and B!='AAAA':
                        foo = topol.BondedParams.get_dihedral_param(a1.type,a2.type,a3.type,a4.type, func)
			#need to check if the dihedral has torsion pre-defined
			counter = check_dih_ILDN(topol,rlist,rdic, a1, a2, a3, a4)
			if( counter == 42 ):
			    continue

                        for ast in foo:
                            if( counter == 0 ):
                                d[5] = ast
                                d.append(ast)
                            else:
                                alus = backup_d[:]
                                alus[5] = ast
                                alus.append(ast)
                                dih9.append(alus)
                            counter = 1


                    elif B == 'AAAA' and A!='AAAA':
                        foo = topol.BondedParams.get_dihedral_param(a1.typeB,a2.typeB,a3.typeB,a4.typeB, func)
                        #need to check if the dihedral has torsion pre-defined
                        counter = check_dih_ILDN(topol,rlist,rdic, a1, a2, a3, a4)
                        if( counter == 42 ):
                            continue

                        for bst in foo:
                            if( counter == 0 ):
                                d[5] = bst
                                d.append(bst)
                            else:
                                alus = backup_d[:]
                                alus[5] = bst
                                alus.append(bst)
                                dih9.append(alus)
                            counter = 1


                    elif A=='AAAA' and B=='AAAA':
			### VG ###
			# disappear/appear dihedrals, do not morphe #
                        if val=='':
                            astate = topol.BondedParams.get_dihedral_param(a1.type,a2.type,a3.type,a4.type, func)
                        else:
                            astate = topol.BondedParams.get_dihedral_param(a1.type,a2.type,a3.type,a4.type, func)
#                            astate.append(val)
                        if types_morphe([a1,a2,a3,a4]):
                            bstate = topol.BondedParams.get_dihedral_param(a1.typeB,a2.typeB,a3.typeB,a4.typeB, func)
                        else:
                            bstate = astate[:] 

                        #need to check if the dihedral has torsion pre-defined
                        counter = check_dih_ILDN(topol,rlist,rdic, a1, a2, a3, a4)

			if( counter == 42): #torsion for both states defined, change nothing
			    continue

			# A state disappears (when going to B)
                        for ast in astate:
			    if(counter == 0):
			        d[5] = ast
				bst = [ ast[0], ast[1], 0.0, ast[-1] ]
				if( len(d)==6 ):
				    d.append(bst)
				else:
				    d[6] = bst
			        counter = 1
                                #print '%s %s %s %s %s %s' % (d[0].id,d[1].id,d[2].id,d[3].id,astate,bstate)
#				print '%s' %d
			    elif( (counter==1) or (counter==3) ):
				alus = backup_d[:]
				alus[5] = ast
				bst = [ ast[0], ast[1], 0.0, ast[-1] ]
				alus.append(bst)
				dih9.append(alus)

			# B state disappears (when going to A)
			# all must go to the new (appendable) dihedrals 
                        for bst in bstate:
			    if( (counter==0) or (counter==1) or (counter==2) ):
			        alus = backup_d[:]
                                ast = [bst[0], bst[1],0.0, bst[-1] ]
                                alus[5] = ast
                                alus.append(bst)
                                dih9.append(alus)
					

                    if astate == None :
                        print 'Error: No dihedral angle found (state A: predefined state B) for:' 
                        print a1.resname, a2.resname, a3.resname, a4.resname
                        print a1.name, a2.name, a3.name, a4.name, func
                        print a1.atomtype, a2.atomtype, a3.atomtype, a4.atomtype
                        print a1.type, a2.type, a3.type, a4.type
                        print a1.atomtypeB, a2.atomtypeB, a3.atomtypeB, a4.atomtypeB
                        print a1.typeB, a2.typeB, a3.typeB, a4.typeB
			print astate
                        print d
                        sys.exit(1)
                        
                    if bstate == None :
                        print 'Error: No dihedral angle found (state B: predefined state A) for:' 
                        print a1.resname, a2.resname, a3.resname, a4.resname
                        print a1.name, a2.name, a3.name, a4.name, func
                        print a1.atomtype, a2.atomtype, a3.atomtype, a4.atomtype
                        print a1.type, a2.type, a3.type, a4.type
                        print a1.atomtypeB, a2.atomtypeB, a3.atomtypeB, a4.atomtypeB
                        print a1.typeB, a2.typeB, a3.typeB, a4.typeB
                        print d
                        sys.exit(1)
                       
		    ### VG ###
		    ### the previous two if sentences will kill the execution if anything goes wrong ###
		    ### therefore, I am not afraid to do d.append() already in the previous steps ###
		    ### VG ###


    topol.dihedrals.extend(dih9)
    print 'log_> Making dihedrals for state B -> %d dihedrals with perturbed atoms' % count
    print 'log_> Removed %d fake dihedrals' % nfake


def get_torsion_multiplicity( name ):
    foo = list(name)
    mult = int(foo[-1])
    return mult

# for ILDN we need to get the #define dihedral entries explicitly
def explicit_defined_dihedrals(filename):
    l = open(filename).readlines()
    output = {}
    for line in l:
        if line.startswith('#define'):
            entr = line.split()
            name = entr[1]
	    params = [9,float(entr[2]),float(entr[3]),int(entr[4])]
            output[name] = params
    return output



def find_predefined_dihedrals(topol, rlist, rdic, ffbonded, dih_predef_default):

    dih9 = [] # here I will accumulate multiple entries of type 9 dihedrals
    explicit_def = explicit_defined_dihedrals(ffbonded)

    for r in rlist:
        idx = r.id - 1
        dih = rdic[r.resname][3]
        imp = rdic[r.resname][2]
        for d in imp+dih:
#	    print '%s' %d[:4]
            al = []
            for name in d[:4]:
                if name.startswith('+'):
                    next = r.chain.residues[idx+1]
                    atom = next.fetch(name[1:])[0]
                    al.append(atom)
                elif name.startswith('-'):
                    prev = r.chain.residues[idx-1]
                    atom = prev.fetch(name[1:])[0]
                    al.append(atom)
                else:
                    atom = r.fetch(name)[0]
                    al.append(atom)

	    ildn_already_found = 0

            for dx in topol.dihedrals:
                func = dx[4]
                if (dx[0].id == al[0].id and \
                   dx[1].id == al[1].id and \
                   dx[2].id == al[2].id and \
                   dx[3].id == al[3].id) or \
                   (dx[0].id == al[3].id and \
                    dx[1].id == al[2].id and \
                    dx[2].id == al[1].id and \
                    dx[3].id == al[0].id):

                    #the following checks are needed for amber99sb*-ildn
                    #do not overwrite proper (type9) with improper (type4)
                    if('default-star' in d[4] and dx[4]==9):
		        print '%s' %d[4]
                        continue
                    #mark the dihedral found for ILDN
		    if( ildn_already_found==1 ):
			break
		    elif ( 'torsion' in d[4] ):#'torsion' in dx[5] ):
			if ( ('torsion' not in dx[5]) ):
			   continue

                    A,B =  check_case(al[:4])
                    paramA = topol.BondedParams.get_dihedral_param(al[0].type,al[1].type,al[2].type,al[3].type, func)
                    paramB = topol.BondedParams.get_dihedral_param(al[0].typeB,al[1].typeB,al[2].typeB,al[3].typeB, func)

		    astate = []
		    bstate = []
		    backup_dx = dx[:]

		    multA = 0
		    multB = 0

                    if d[4] == 'default-A':
			dih_predef_default.append(dx)
                        astate = paramA
                    elif d[4] == 'default-B':
			dih_predef_default.append(dx)
                        astate = paramB
                    elif d[4] == 'default-star':
			foo  = [4, 105.4, 0.75, 1]
			astate.append(foo)
		    elif 'torsion' in d[4]:
			foo = explicit_def[d[4]]
			astate.append(foo)
			ildn_already_found = 1
			func = 9
                    elif d[4] == 'undefined':
			dih_predef_default.append(dx)
                        astate = ''
                    else:
                        astate = d[4]

                    if d[5] == 'default-A':
                        bstate = paramA
                    elif d[5] == 'default-B':
                        bstate = paramB
                    elif d[5] == 'default-star':
                        foo = [4, 105.4, 0.75, 1]
			bstate.append(foo)
                    elif 'torsion' in d[5]:
                        foo = explicit_def[d[5]]
			bstate.append(foo)
			ildn_already_found = 1
			func = 9
                    elif d[5] == 'undefined' :
                        bstate = ''
                    else:
                        bstate = d[5]
		
#		    print '%s' %d[4]
		    print '%d %d' %(multA,multB)

		    ### VG ###
		    # this should work for ILDN #
                    counter = 0
                    for foo in astate:
			if( counter == 0 ):
			    dx[4] = func
		            dx[5] = foo
                            bar = [foo[0], foo[1],0.0, foo[-1] ]
                            dx.append(bar)
			else:
  			    alus = backup_dx[:]
			    alus[5] = foo
                            bar = [foo[0], foo[1],0.0, foo[-1] ]
			    alus.append(bar)
			    dih9.append(alus)
#			print 'INLOOP %s %s' % (foo,bar)
                        counter = 1

                    for foo in bstate:
                        alus = backup_dx[:]
                        bar = [foo[0], foo[1],0.0, foo[-1] ]
                        alus[5] = bar
                        alus.append(foo)
                        dih9.append(alus)
#			print 'BINLOOP %s %s %s' % (bar,foo,d[5])
#		    print '%s' % dx
#		    print '%s' % dih9
#		    print ''


    topol.dihedrals.extend(dih9)



class mtpError(Exception):
    def __init__(self,s):
        self.s = s
    def __str__(self):
        return repr(self.s)

def get_hybrid_residue(residue_name, mtp_file = 'ffamber99sb.mtp', version = 'old'):
    print 'log_> Scanning database for %s ' % residue_name
    resi, bonds, imps, diheds, rotdic = read_mtp_entry(residue_name, filename = mtp_file, version = version)
    if len(resi.atoms) == 0:
        raise mtpError("Hybrid residue %s not found in %s" % (residue_name, mtp_file) )
    return resi, bonds, imps, diheds, rotdic


def is_hybrid_residue( resname ):
    if resname in _perturbed_nucleotides or \
       resname[1] == '2':
        return True
    else: return False



def change_outfile_format(filename, ext):
    head, tail = os.path.split(filename)
    name, ex = os.path.splitext(tail)
    new_name = os.path.join(head, name+'.'+ext)
    return new_name
    
def get_hybrid_residues( m, mtp_file, version ):
    rdic = {}
    rlist = []
    for res in m.residues:
        if is_hybrid_residue( res.resname ):
            rlist.append( res )
            mtp = get_hybrid_residue( res.resname, mtp_file, version )
            rdic[res.resname] = mtp
            hybrid_res = mtp[0]
            atom_names = map(lambda a: a.name, hybrid_res.atoms )
            atoms = res.fetchm( atom_names )
            for i, atom in enumerate( hybrid_res.atoms ):
                atoms[i].atomtypeB = atom.atomtypeB
                atoms[i].qB = atom.qB
                atoms[i].mB = atom.mB
    return rlist, rdic


def __add_extra_DNA_impropers(  topol, rlist, func_type, stateA, stateB ):
    extra_impropers = []
    for r in rlist:
        if r.resname in  ['DAT','DAC','DGC','DGT','RAU','RAC','RGC','RGU']:
            print 'Adding extra improper dihedrals for residue %d-%s' % (r.id, r.resname)
            alist = r.fetchm(['C1\'','N9','C8','DC2'])
            extra_impropers.append( alist )
            alist = r.fetchm(['C1\'','N9','C4','DC6'])
            extra_impropers.append( alist )
        elif r.resname in ['DTA','DTG','DCG','DCA','RUA','RUG','RCG','RCA']:
            print 'Adding extra improper dihedrals for residue %d-%s' % (r.id, r.resname)
            alist = r.fetchm(['C1\'','N1','C6','DC4'])
            extra_impropers.append( alist )
            alist = r.fetchm(['C1\'','N1','C2','DC8'])
            extra_impropers.append( alist )
    for imp in extra_impropers:
        imp.extend( [func_type, [func_type]+stateA, [func_type]+stateB] )
    topol.dihedrals += extra_impropers


def __atoms_morphe( atoms ):
    for atom in atoms:
        if atom.atomtypeB is not None and (atom.q!=atom.qB or atom.m != atom.mB): return True
    return False
    

def sum_charge_of_states(rlist):
    qA = []
    qB = []
    for r in rlist:
        qa = 0
        qb = 0
        for atom in r.atoms:
            qa+=atom.q
            if __atoms_morphe([atom]):
                qb+=atom.qB
            else:
                qb+=atom.q
        qA.append(qa)
        qB.append(qb)
    return qA, qB


def get_ff_path( ff ):
    ff_path = None
    if not os.path.isdir(ff):
	### VG ###
	gmxlib = os.environ.get('GMXDATA') 
    #    gmxlib = os.environ.get('GMXDATA')
	p = os.path.join(gmxlib,ff)
    #    p = os.path.join( os.path.join(gmxlib,'top'), ff)
	### VG ###
        if not os.path.isdir(p):
            print >>sys.stderr,' Error: forcefield path "%s" not found' % ff
        else:
            ff_path = p
    else:
        ff_path = ff
    print 'Opening forcefield: %s' % ff_path
    return ff_path

def main(argv):
    
    options = [
        Option( "-split", "bool", False, "Write splitted topologies for vdw and q morphes"),
        Option( "-scale_mass", "bool", True, "scale_mass"),
        ]
    
    files = [
        FileOption("-p", "r",["top"],"topol.top", "Input Topology File"),
        FileOption("-itp", "r",["itp"],"topol.top", "Optional Input ITP  File"),
        FileOption("-o", "w",["top","itp"],"newtop.top", "Topology or ITP output file "),
        FileOption("-ff", "dir",["ff"],"amber99sbmut.ff", "Mutation force field "),
        FileOption("-log", "w",["log"],"bstate.log", "Log file"),
        ]
    
    help_text = ['']
    cmdl = Commandline( argv, options = options,
                        fileoptions = files,
                        program_desc = help_text,
                        check_for_existing_files = False )

    
    do_scale_mass = cmdl['-scale_mass']
    top_file = cmdl['-p']
    out_file = cmdl['-o']
    log_file = cmdl['-log']
    mtp_file = os.path.join( get_ff_path(cmdl['-ff']), 'mutres.mtp')
    ffbonded_file = os.path.join( get_ff_path(cmdl['-ff']), 'ffbonded.itp')
    do_split = cmdl['-split']
    if cmdl.opt['-itp'].is_set:
        input_itp = cmdl['-itp']
    else:
        input_itp = None
    if input_itp and out_file.split('.')[-1] != 'itp':
        out_file = change_outfile_format(out_file, 'itp')
        print 'log_> Setting outfile name to %s' % out_file



    if input_itp:
        print 'log_> Reading input files "%s" and "%s"' % (top_file, input_itp)
        topol = Topology( input_itp,  topfile = top_file, version = 'new')
    else:
        print 'log_> Reading input file "%s"' % (top_file)
        topol = Topology( top_file, version = 'new' )


    m = Model( atoms = topol.atoms )     # create model with residue list
    topol.residues = m.residues          # use model residue list
    rlist, rdic = get_hybrid_residues( m, mtp_file, version = 'new')
    topol.assign_fftypes()               # correct b-states
    for r in rlist:
        print 'log_> Hybrid Residue -> %d | %s ' % (r.id, r.resname )


    find_bonded_entries( topol )
    find_angle_entries( topol )

    dih_predef_default = []
    find_predefined_dihedrals(topol,rlist,rdic,ffbonded_file,dih_predef_default)
    find_dihedral_entries( topol, rlist, rdic, dih_predef_default )

    __add_extra_DNA_impropers(topol, rlist,   1, [180,40,2],[180,40,2])
    qA, qB = sum_charge_of_states( rlist )
    qA_mem = copy.deepcopy( qA )
    qB_mem = copy.deepcopy( qB )
    
    print 'log_> Total charge of state A = ', topol.get_qA()
    print 'log_> Total charge of state B = ', topol.get_qB()

    topol.write( out_file, scale_mass = do_scale_mass, target_qB = qB )

#    topol.check_special_dihedrals( )
    # done normal topology for full switch


    if cmdl['-split']: # write splitted topology
        root, ext = os.path.splitext(out_file)
        out_file_qoff = root+'_qoff'+ext
        out_file_vdw = root+'_vdw'+ext
        out_file_qon = root+'_qon'+ext

        print '------------------------------------------------------'
        print 'log_> Creating splitted topologies............'
        print 'log_> Making "qoff" topology : "%s"' % out_file_qoff
        contQ = copy.deepcopy(qA_mem)
        topol.write( out_file_qoff, stateQ = 'AB', stateTypes = 'AA', dummy_qB='off',
                         scale_mass = do_scale_mass, target_qB = qA, stateBonded = 'AA', full_morphe = False )
        print 'log_> Charge of state A: %g' % topol.qA
        print 'log_> Charge of state B: %g' % topol.qB

        print '------------------------------------------------------'
        print 'log_> Making "vdw" topology : "%s"' % out_file_vdw
        contQ = copy.deepcopy(qA_mem)
        topol.write( out_file_vdw, stateQ = 'BB', stateTypes = 'AB', dummy_qA='off', dummy_qB = 'off',
                         scale_mass = do_scale_mass, target_qB = contQ, stateBonded = 'AB' , full_morphe = False)
        print 'log_> Charge of state A: %g' % topol.qA
        print 'log_> Charge of state B: %g' % topol.qB
        print '------------------------------------------------------'

        print 'log_> Making "qon" topology : "%s"' % out_file_qon
        topol.write( out_file_qon, stateQ = 'BB', stateTypes = 'BB', dummy_qA='off', dummy_qB = 'on',
                         scale_mass = do_scale_mass, target_qB = qB_mem,  stateBonded = 'BB' , full_morphe = False)
        print 'log_> Charge of state A: %g' % topol.qA
        print 'log_> Charge of state B: %g' % topol.qB
        print '------------------------------------------------------'

    print
    print 'making b-states done...........'
    print

if __name__=='__main__':
    main(sys.argv)

