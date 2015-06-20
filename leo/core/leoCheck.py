# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20150605175037.1: * @file leoCheck.py
#@@first
'''Experimental code checking for Leo.'''
import leo.core.leoGlobals as g
import leo.core.leoAst as leoAst
import ast
import glob
import re
import time
#@+others
#@+node:ekr.20150606024455.1: ** class ShowDataTraverser
class ShowDataTraverser(leoAst.AstFullTraverser):
    '''
    Add data about classes, defs, returns and calls to controller's dictionaries.

    Sets .context and .parent ivars before visiting each node.
    '''

    def __init__(self, controller, fn):
        '''Ctor for AstFullTraverser class.'''
        module_tuple = g.shortFileName(fn), 'module', g.shortFileName(fn)
            # fn, kind, s.
        self.context_stack = [module_tuple]
        self.controller = controller
        self.fn = g.shortFileName(fn)
        self.formatter = leoAst.AstFormatter()
            # leoAst.AstPatternFormatter()
        self.trace = False
    #@+others
    #@+node:ekr.20150609053332.1: *3* sd.Helpers
    #@+node:ekr.20150606035006.1: *4* sd.context_names
    def context_names(self):
        '''Return the present context names.'''
        result = []
        n = len(self.context_stack)
        for i in n - 1, n - 2:
            if i >= 0:
                fn, kind, s = self.context_stack[i]
                assert kind in ('class', 'def', 'module'), kind
                if kind == 'module':
                    result.append(s.strip())
                else:
                    # Append the name following the class or def.
                    i = g.skip_ws(s, 0)
                    i += len(kind)
                    i = g.skip_ws(s, i)
                    j = g.skip_c_id(s, i)
                    result.append(s[i: j])
            else:
                result.append('')
                break
        # g.trace(list(reversed(result)))
        return reversed(result)
    #@+node:ekr.20150609053010.1: *4* sd.format
    def format(self, node):
        '''Return the formatted version of an Ast Node.'''
        return self.formatter.format(node).strip()
    #@+node:ekr.20150606024455.62: *4* sd.visit
    def visit(self, node):
        '''Visit a *single* ast node.  Visitors are responsible for visiting children!'''
        method = getattr(self, 'do_' + node.__class__.__name__)
        method(node)

    def visit_children(self, node):
        assert False, 'must visit children explicitly'
    #@+node:ekr.20150609052952.1: *3* sd.Visitors
    #@+node:ekr.20150607200422.1: *4* sd.Assign
    # Assign(expr* targets, expr value)

    def do_Assign(self, node):
        # Visit and format.
        value = self.format(self.visit(node.value))
        assign_tuples = []
        for target in node.targets:
            target = self.format(self.visit(target))
            s = '%s=%s' % (target, value)
            context2, context1 = self.context_names()
            assign_tuple = context2, context1, s
            assign_tuples.append(assign_tuple)
            # Update data.
            aList = self.controller.assigns_d.get(target, [])
            aList.extend(assign_tuples)
            self.controller.calls_d[target] = aList
    #@+node:ekr.20150607200439.1: *4* sd.AugAssign
    # AugAssign(expr target, operator op, expr value)

    def do_AugAssign(self, node):
        # Visit and update data.
        target = self.format(self.visit(node.target))
        s = '%s=%s' % (target, self.format(self.visit(node.value)))
        context2, context1 = self.context_names()
        assign_tuple = context2, context1, s
        aList = self.controller.assigns_d.get(target, [])
        aList.append(assign_tuple)
        self.controller.calls_d[target] = aList
    #@+node:ekr.20150606024455.16: *4* sd.Call
    # Call(expr func, expr* args, keyword* keywords, expr? starargs, expr? kwargs)

    def do_Call(self, node):
        # Update data
        s = self.format(node)
        name = self.format(node.func)
        context2, context1 = self.context_names()
        call_tuple = context2, context1, s
        aList = self.controller.calls_d.get(name, [])
        aList.append(call_tuple)
        self.controller.calls_d[name] = aList
        # Visit.
        self.visit(node.func)
        for z in node.args:
            self.visit(z)
        for z in node.keywords:
            self.visit(z)
        if getattr(node, 'starargs', None):
            self.visit(node.starargs)
        if getattr(node, 'kwargs', None):
            self.visit(node.kwargs)
    #@+node:ekr.20150606024455.3: *4* sd.ClassDef
    # ClassDef(identifier name, expr* bases, stmt* body, expr* decorator_list)

    def do_ClassDef(self, node):
        # Format.
        if node.bases:
            bases = [self.format(z) for z in node.bases]
            s = 'class %s(%s):' % (node.name, ','.join(bases))
        else:
            s = 'class %s:' % node.name
        if self.trace: g.trace(s)
        # Enter the new context.
        context_tuple = self.fn, 'class', s
        self.context_stack.append(context_tuple)
        # Update controller data.
        class_tuple = self.context_stack[: -1], s
        aList = self.controller.classes_d.get(node.name, [])
        aList.append(class_tuple)
        self.controller.classes_d[node.name] = aList
        # Visit.
        for z in node.bases:
            self.visit(z)
        for z in node.body:
            self.visit(z)
        for z in node.decorator_list:
            self.visit(z)
        # Leave the context.
        self.context_stack.pop()
    #@+node:ekr.20150606024455.4: *4* sd.FunctionDef
    # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)

    def do_FunctionDef(self, node):
        # Format.
        args = self.format(node.args) if node.args else ''
        s = 'def %s(%s):' % (node.name, args)
        if self.trace: g.trace(s)
        # Enter the new context.
        context_tuple = self.fn, 'def', s
        self.context_stack.append(context_tuple)
        # Update controller data.
        def_tuple = self.context_stack[: -1], s
        aList = self.controller.defs_d.get(node.name, [])
        aList.append(def_tuple)
        self.controller.defs_d[node.name] = aList
        # Visit.
        for z in node.decorator_list:
            self.visit(z)
        self.visit(node.args)
        for z in node.body:
            self.visit(z)
        # Leave the context.
        self.context_stack.pop()
    #@+node:ekr.20150606024455.55: *4* sd.Return
    # Return(expr? value)

    def do_Return(self, node):
        # Format...
        s = self.format(node)
        if self.trace: g.trace(s)
        # Update data
        context, name = self.context_names()
        aList = self.controller.returns_d.get(name, [])
        return_tuple = context, s
        aList.append(return_tuple)
        self.controller.returns_d[name] = aList
        # Visit.
        if node.value:
            self.visit(node.value)
    #@-others
#@+node:ekr.20150525123715.1: ** class ProjectUtils
class ProjectUtils:
    '''A class to compute the files in a project.'''
    # To do: get project info from @data nodes.
    #@+others
    #@+node:ekr.20150525123715.2: *3* pu.files_in_dir
    def files_in_dir(self, theDir, recursive=True, extList=None, excludeDirs=None):
        '''
        Return a list of all Python files in the directory.
        Include all descendants if recursiveFlag is True.
        Include all file types if extList is None.
        '''
        import glob
        import os
        # if extList is None: extList = ['.py']
        if excludeDirs is None: excludeDirs = []
        result = []
        if recursive:
            for root, dirs, files in os.walk(theDir):
                for z in files:
                    fn = g.os_path_finalize_join(root, z)
                    junk, ext = g.os_path_splitext(fn)
                    if not extList or ext in extList:
                        result.append(fn)
                if excludeDirs and dirs:
                    for z in dirs:
                        if z in excludeDirs:
                            dirs.remove(z)
        else:
            for ext in extList:
                result.extend(glob.glob('%s.*%s' % (theDir, ext)))
        return sorted(list(set(result)))
    #@+node:ekr.20150525123715.3: *3* pu.get_project_directory
    def get_project_directory(self, name):
        # Ignore everything after the first space.
        i = name.find(' ')
        if i > -1:
            name = name[: i].strip()
        leo_path, junk = g.os_path_split(__file__)
        d = {
            # Change these paths as required for your system.
            'coverage': r'C:\Python26\Lib\site-packages\coverage-3.5b1-py2.6-win32.egg\coverage',
            'leo': r'C:\leo.repo\leo-editor\leo\core',
            'lib2to3': r'C:\Python26\Lib\lib2to3',
            'pylint': r'C:\Python26\Lib\site-packages\pylint',
            'rope': r'C:\Python26\Lib\site-packages\rope-0.9.4-py2.6.egg\rope\base',
            'test': g.os_path_finalize_join(g.app.loadDir, '..', 'test-proj'),
        }
        dir_ = d.get(name.lower())
        # g.trace(name,dir_)
        if not dir_:
            g.trace('bad project name: %s' % (name))
        if not g.os_path_exists(dir_):
            g.trace('directory not found:' % (dir_))
        return dir_ or ''
    #@+node:ekr.20150525123715.4: *3* pu.project_files
    def project_files(self, name, force_all=False):
        '''Return a list of all files in the named project.'''
        # Ignore everything after the first space.
        i = name.find(' ')
        if i > -1:
            name = name[: i].strip()
        leo_path, junk = g.os_path_split(__file__)
        d = {
            # Change these paths as required for your system.
            'coverage': (
                r'C:\Python26\Lib\site-packages\coverage-3.5b1-py2.6-win32.egg\coverage',
                ['.py'], ['.bzr', 'htmlfiles']),
            'leo': (
                r'C:\leo.repo\leo-editor\leo\core',
                ['.py'], ['.git']), # ['.bzr']
            'lib2to3': (
                r'C:\Python26\Lib\lib2to3',
                ['.py'], ['tests']),
            'pylint': (
                r'C:\Python26\Lib\site-packages\pylint',
                ['.py'], ['.bzr', 'test']),
            'rope': (
                r'C:\Python26\Lib\site-packages\rope-0.9.4-py2.6.egg\rope\base', ['.py'], ['.bzr']),
            # 'test': (
                # g.os_path_finalize_join(leo_path,'test-proj'),
                # ['.py'],['.bzr']),
        }
        data = d.get(name.lower())
        if not data:
            g.trace('bad project name: %s' % (name))
            return []
        theDir, extList, excludeDirs = data
        files = self.files_in_dir(theDir, recursive=True, extList=extList, excludeDirs=excludeDirs)
        if files:
            if name.lower() == 'leo':
                for exclude in ['__init__.py', 'format-code.py']:
                    files = [z for z in files if not z.endswith(exclude)]
                table = (
                    r'C:\leo.repo\leo-editor\leo\commands',
                    # r'C:\leo.repo\leo-editor\leo\plugins\importers',
                    # r'C:\leo.repo\leo-editor\leo\plugins\writers',
                )
                for dir_ in table:
                    files2 = self.files_in_dir(dir_, recursive=True, extList=['.py',], excludeDirs=[])
                    files2 = [z for z in files2 if not z.endswith('__init__.py')]
                    # g.trace(g.os_path_exists(dir_), dir_, '\n'.join(files2))
                    files.extend(files2)
                files.extend(glob.glob(r'C:\leo.repo\leo-editor\leo\plugins\qt_*.py'))
                fn = g.os_path_finalize_join(theDir, '..', 'plugins', 'qtGui.py')
                if fn and g.os_path_exists(fn):
                    files.append(fn)
            if g.app.runningAllUnitTests and len(files) > 1 and not force_all:
                return [files[0]]
        if not files:
            g.trace(theDir)
        if g.app.runningAllUnitTests and len(files) > 1 and not force_all:
            return [files[0]]
        else:
            return files
    #@-others
#@+node:ekr.20150604164113.1: ** class ShowData
class ShowData:
    #@+others
    #@+node:ekr.20150604165500.1: *3*  ctor
    def __init__(self, c):
        self.c = c
        # Data.
        self.assigns_d = {}
        self.calls_d = {}
        self.classes_d = {}
        self.context_stack = []
        self.context_indent = -1
        self.defs_d = {}
        self.files = None
        self.returns_d = {}
        # Statistics
        self.n_matches = 0
        self.tot_lines = 0
        self.tot_s = 0
        self.n_undefined_calls = 0
        # Regex patterns used by match.  A brilliant prototype.
        r_class = r'class[ \t]+([a-z_A-Z][a-z_A-Z0-9]*).*:'
        r_def = r'def[ \t]+([a-z_A-Z][a-z_A-Z0-9]*)[ \t]*\((.*)\)'
        r_return = r'(return[ \t].*)$'
        r_call = r'([a-z_A-Z][a-z_A-Z0-9]*)[ \t]*\(([^)]*)\)'
        self.r_all = re.compile('|'.join([r_class, r_def, r_return, r_call,]))
    #@+node:ekr.20150604163903.1: *3* run & helpers
    def run(self, files):
        '''Process all files'''
        self.files = files
        t1 = time.clock()
        for fn in files:
            s, e = g.readFileIntoString(fn)
            if s:
                self.tot_s += len(s)
                g.trace('%8s %s' % ("{:,}".format(len(s)), g.shortFileName(fn)))
                # Fast, accurate:
                # 1.9 sec for parsing.
                # 2.5 sec for Null AstFullTraverer traversal.
                # 2.7 sec to generate all strings.
                # 3.8 sec to generate all reports.
                s1 = g.toEncodedString(s)
                self.tot_lines += len(g.splitLines(s))
                    # Adds less than 0.1 sec.
                node = ast.parse(s1, filename='before', mode='exec')
                ShowDataTraverser(self, fn).visit(node)
                # elif 0: # Too slow, too clumsy: 3.3 sec for tokenizing
                    # readlines = g.ReadLinesClass(s).next
                    # for token5tuple in tokenize.generate_tokens(readlines):
                        # pass
                # else: # Inaccurate. 2.2 sec to generate all reports.
                    # self.scan(fn, s)
            else:
                g.trace('skipped', g.shortFileName(fn))
        t2 = time.clock()
            # Get the time exlusive of print time.
        self.show_results()
        g.trace('done: %4.1f sec.' % (t2 - t1))
    #@+node:ekr.20150604164546.1: *3* show_results & helpers
    def show_results(self):
        '''Print a summary of the test results.'''
        make = True
        multiple_only = True # True only show defs defined in more than one place.
        c = self.c
        result = ['@killcolor']
        for name in sorted(self.defs_d):
            aList = self.defs_d.get(name, [])
            if len(aList) > 1 or not multiple_only: # not name.startswith('__') and (
                self.show_defs(name, result)
                self.show_calls(name, result)
                self.show_returns(name, result)
        self.show_undefined_calls(result)
        # Put the result in a new node.
        summary = 'files: %s lines: %s chars: %s classes: %s\ndefs: %s calls: %s undefined calls: %s returns: %s' % (
            # self.plural(self.files),
            len(self.files),
            "{:,}".format(self.tot_lines),
            "{:,}".format(self.tot_s),
            "{:,}".format(len(self.classes_d.keys())),
            "{:,}".format(len(self.defs_d.keys())),
            "{:,}".format(len(self.calls_d.keys())),
            "{:,}".format(self.n_undefined_calls),
            "{:,}".format(len(self.returns_d.keys())),
        )
        result.insert(1, summary)
        result.extend(['', summary])
        if make:
            last = c.lastTopLevel()
            p2 = last.insertAfter()
            p2.h = 'global signatures'
            p2.b = '\n'.join(result)
            c.redraw(p=p2)
        print(summary)
    #@+node:ekr.20150605163128.1: *4* plural
    def plural(self, aList):
        return 's' if len(aList) > 1 else ''
    #@+node:ekr.20150605160218.1: *4* show_calls
    def show_calls(self, name, result):
        aList = self.calls_d.get(name, [])
        if not aList:
            return
        result.extend(['', '    %s call%s...' % (len(aList), self.plural(aList))])
        w = 0
        calls = sorted(set(aList))
        for call_tuple in calls:
            context2, context1, s = call_tuple
            w = max(w, len(context2 or '') + len(context1 or ''))
        for call_tuple in calls:
            context2, context1, s = call_tuple
            pad = w - (len(context2 or '') + len(context1 or ''))
            if context2:
                result.append('%s%s::%s: %s' % (
                    ' ' * (8 + pad), context2, context1, s))
            else:
                result.append('%s%s: %s' % (
                    ' ' * (10 + pad), context1, s))
    #@+node:ekr.20150605155601.1: *4* show_defs
    def show_defs(self, name, result):
        aList = self.defs_d.get(name, [])
        name_added = False
        w = 0
        # Calculate the width
        for def_tuple in aList:
            context_stack, s = def_tuple
            if context_stack:
                fn, kind, context_s = context_stack[-1]
                w = max(w, len(context_s))
        for def_tuple in aList:
            context_stack, s = def_tuple
            if not name_added:
                name_added = True
                result.append('\n%s' % name)
                result.append('    %s definition%s...' % (len(aList), self.plural(aList)))
            if context_stack:
                fn, kind, context_s = context_stack[-1]
                def_s = s.strip()
                pad = w - len(context_s)
                result.append('%s%s: %s' % (' ' * (8 + pad), context_s, def_s))
            else:
                result.append('%s%s' % (' ' * 4, s.strip()))
    #@+node:ekr.20150605160341.1: *4* show_returns
    def show_returns(self, name, result):
        aList = self.returns_d.get(name, [])
        if not aList:
            return
        result.extend(['', '    %s return%s...' % (len(aList), self.plural(aList))])
        w, returns = 0, sorted(set(aList))
        for returns_tuple in returns:
            context, s = returns_tuple
            w = max(w, len(context or ''))
        for returns_tuple in returns:
            context, s = returns_tuple
            pad = w - len(context)
            result.append('%s%s: %s' % (' ' * (8 + pad), context, s))
    #@+node:ekr.20150606092147.1: *4* show_undefined_calls
    def show_undefined_calls(self, result):
        '''Show all calls to undefined functions.'''
        # g.trace(sorted(self.defs_d.keys()))
        call_tuples = []
        for s in self.calls_d:
            i = 0
            while True:
                progress = i
                j = s.find('.', i)
                if j == -1:
                    name = s[i:].strip()
                    call_tuple = name, s
                    call_tuples.append(call_tuple)
                    break
                else:
                    i = j + 1
                assert progress < i
        undef = []
        for call_tuple in call_tuples:
            name, s = call_tuple
            if name not in self.defs_d:
                undef.append(call_tuple)
        undef = list(set(undef))
        result.extend(['', '%s undefined call%s...' % (
            len(undef), self.plural(undef))])
        self.n_undefined_calls = len(undef)
        # Merge all the calls for name.
        # There may be several with different s values.
        results_d = {}
        for undef_tuple in undef:
            name, s = undef_tuple
            calls = self.calls_d.get(s, [])
            aList = results_d.get(name, [])
            for call_tuple in calls:
                aList.append(call_tuple)
            results_d[name] = aList
        # Print the final results.
        for name in sorted(results_d):
            calls = results_d.get(name)
            result.extend(['', '%s %s call%s...' % (name, len(calls), self.plural(calls))])
            w = 0
            for call_tuple in calls:
                context2, context1, s = call_tuple
                if context2:
                    w = max(w, 2 + len(context2) + len(context1))
                else:
                    w = max(w, len(context1))
            for call_tuple in calls:
                context2, context1, s = call_tuple
                pad = w - (len(context2) + len(context1))
                if context2:
                    result.append('%s%s::%s: %s' % (
                        ' ' * (2 + pad), context2, context1, s))
                else:
                    result.append('%s%s: %s' % (
                        ' ' * (2 + pad), context1, s))
    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@@pagewidth 70
#@-leo