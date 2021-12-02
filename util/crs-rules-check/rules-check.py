#!/usr/bin/env python3

import sys
import os
import glob
import msc_pyparser
import difflib
import argparse

oformat = "native"

class Check(object):
    def __init__(self, data):

        # list available operators, actions, transformations and ctl args
        self.operators   = "beginsWith|containsWord|contains|detectSQLi|detectXSS|endsWith|eq|fuzzyHash|geoLookup|ge|gsbLookup|gt|inspectFile|ipMatch|ipMatchF|ipMatchFromFile|le|lt|noMatch|pmFromFile|pmf|pm|rbl|rsub|rx|streq|strmatch|unconditionalMatch|validateByteRange|validateDTD|validateHash|validateSchema|validateUrlEncoding|validateUtf8Encoding|verifyCC|verifyCPF|verifySSN|within".split("|")
        self.operatorsl  = [o.lower() for o in self.operators]
        self.actions     = "accuracy|allow|append|auditlog|block|capture|chain|ctl|deny|deprecatevar|drop|exec|expirevar|id|initcol|logdata|log|maturity|msg|multiMatch|noauditlog|nolog|pass|pause|phase|prepend|proxy|redirect|rev|sanitiseArg|sanitiseMatched|sanitiseMatchedBytes|sanitiseRequestHeader|sanitiseResponseHeader|setenv|setrsc|setsid|setuid|setvar|severity|skipAfter|skip|status|tag|t|ver|xmlns".split("|")
        self.actionsl    = [a.lower() for a in self.actions]
        self.transforms  = "base64DecodeExt|base64Decode|base64Encode|cmdLine|compressWhitespace|cssDecode|escapeSeqDecode|hexDecode|hexEncode|htmlEntityDecode|jsDecode|length|lowercase|md5|none|normalisePathWin|normalisePath|normalizePathWin|normalizePath|parityEven7bit|parityOdd7bit|parityZero7bit|removeCommentsChar|removeComments|removeNulls|removeWhitespace|replaceComments|replaceNulls|sha1|sqlHexDecode|trimLeft|trimRight|trim|uppercase|urlDecodeUni|urlDecode|urlEncode|utf8toUnicode".split("|")
        self.transformsl = [t.lower() for t in self.transforms]
        self.ctls        = "auditEngine|auditLogParts|debugLogLevel|forceRequestBodyVariable|hashEnforcement|hashEngine|requestBodyAccess|requestBodyLimit|requestBodyProcessor|responseBodyAccess|responseBodyLimit|ruleEngine|ruleRemoveById|ruleRemoveByMsg|ruleRemoveByTag|ruleRemoveTargetById|ruleRemoveTargetByMsg|ruleRemoveTargetByTag".split("|")
        self.ctlsl       = [c.lower() for c in self.ctls]

        # list the actions in expected order
        # see wiki: https://github.com/SpiderLabs/owasp-modsecurity-crs/wiki/Order-of-ModSecurity-Actions-in-CRS-rules
        # note, that these tokens are with lovercase here, but used only for to check the order
        self.ordered_actions = [
            "id",                   # 0
            "phase",                # 1
            "allow",
            "block",
            "deny",
            "drop",
            "pass",
            "proxy",
            "redirect",
            "status",
            "capture",              # 10
            "t",
            "log",
            "nolog",
            "auditlog",
            "noauditlog",
            "msg",
            "logdata",
            "tag",
            "sanitisearg",
            "sanitiserequestheader",    # 20
            "sanitisematched",
            "sanitisematchedbytes",
            "ctl",
            "ver",
            "severity",
            "multimatch",
            "initcol",
            "setenv",
            "setvar",
            "expirevar",            # 30
            "chain",
            "skip",
            "skipafter",
        ]

        self.data           = data  # holds the parsed data
        self.current_ruleid = 0     # holds the rule id
        self.curr_lineno    = 0     # current line number
        self.chained        = False # holds the chained flag
        self.caseerror      = []    # list of case mismatch errors
        self.orderacts      = []    # list of ordered action errors

    def store_error(self, prefix, actstr):
        # store the error msg in the list
        # if no rule id (wrong rule), then stores the line number
        if self.current_ruleid > 0:
            pval = self.current_ruleid
            ptype = "rule ID"
        else:
            pval = self.curr_lineno
            ptype = "line"
        self.caseerror.append("%s: %d, %s in %s" % (ptype, pval, prefix, actstr))

    def check_ignore_case(self):
        # check the ignore cases at operators, actions,
        # transformations and ctl arguments
        for d in self.data:
            if "actions" in d:
                aidx = 0        # index of action in list
                if self.chained == False:
                    self.current_ruleid = 0
                else:
                    self.chained = False

                while aidx < len(d['actions']):
                    a = d['actions'][aidx]  # 'a' is the action from the list

                    self.curr_lineno = a['lineno']
                    if a['act_name'] == "id":
                        self.current_ruleid = int(a['act_arg'])

                    if a['act_name'] == "chain":
                        self.chained = True

                    # check the action is valid
                    if a['act_name'].lower() not in self.actionsl:
                        self.store_error("Invalid action", a['act_name'])
                    # check the action case sensitive format
                    if self.actions[self.actionsl.index(a['act_name'].lower())] != a['act_name']:
                        self.store_error("Action case mismatch", a['act_name'])

                    if a['act_name'] == 'ctl':
                        # check the ctl argument is valid
                        if a['act_arg'].lower() not in self.ctlsl:
                            self.store_error("Invalid ctl", a['act_arg'])
                        # check the ctl argument case sensitive format
                        if self.ctls[self.ctlsl.index(a['act_arg'].lower())] != a['act_arg']:
                            self.store_error("Ctl case mismatch", a['act_arg'])
                    if a['act_name'] == 't':
                        # check the transform is valid
                        if a['act_arg'].lower() not in self.transformsl:
                            self.store_error("Invalid transform", a['act_arg'])
                        # check the transform case sensitive format
                        if self.transforms[self.transformsl.index(a['act_arg'].lower())] != a['act_arg']:
                            self.store_error("Transform case mismatch", a['act_arg'])
                    aidx += 1
            if "operator" in d and d["operator"] != "":
                self.curr_lineno = d['oplineno']
                # strip the operator
                op = d['operator'].replace("!", "").replace("@", "")
                # check the operator is valid
                if op.lower() not in self.operatorsl:
                    self.store_error("Invalid operator", d['operator'])
                # check the operator case sensitive format
                if self.operators[self.operatorsl.index(op.lower())] != op:
                    self.store_error("Operator case mismatch", d['operator'])

    def check_action_order(self):
        for d in self.data:
            if "actions" in d:
                aidx = 0        # stores the index of current action
                max_order = 0   # maximum position of readed actions
                if self.chained == False:
                    self.current_ruleid = 0
                else:
                    self.chained = False

                while aidx < len(d['actions']):
                    # read the action into 'a'
                    a = d['actions'][aidx]

                    # get the 'id' of rule
                    self.curr_lineno = a['lineno']
                    if a['act_name'] == "id":
                        self.current_ruleid = int(a['act_arg'])

                    # check if chained
                    if a['act_name'] == "chain":
                        self.chained = True

                    # get the index of action from the ordered list
                    # above from constructor
                    try:
                        act_idx = self.ordered_actions.index(a['act_name'].lower())
                    except ValueError:
                        errmsg("ERROR: '%s' not in actions list!" % (a['act_name']))
                        sys.exit(-1)

                    # if the index of current action is @ge than the previous
                    # max value, load it into max_order
                    if act_idx >= max_order:
                        max_order = act_idx
                    else:
                        # prevact is the previous action's position in list
                        # act_idx is the current action's position in list
                        # if the prev is @gt actually, means it's at wrong position
                        if self.ordered_actions.index(prevact) > act_idx:
                            self.orderacts.append([0, prevact, pidx, a['act_name'], aidx, self.ordered_actions.index(prevact), act_idx])
                    prevact = a['act_name'].lower()
                    pidx = aidx
                    aidx += 1
                for a in self.orderacts:
                    if a[0] == 0:
                        a[0] = self.current_ruleid

def errmsg(msg):
    if oformat == "github":
        print("::error %s" % (msg))
    else:
        print(msg)

def msg(msg):
    if oformat == "github":
        print("::debug %s" % (msg))
    else:
        print(msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRS Rules Check tool")
    parser.add_argument("--output", dest="output", help="Output format native[default]|github", required=False)
    parser.add_argument('crspath', metavar='/path/to/coreruleset/*.conf', type=str,
                        help='Directory path to CRS')
    args = parser.parse_args()

    crspath = args.crspath

    if args.output is not None:
        if args.output not in ["native", "github"]:
            print("--output can be one of the 'native' or 'github'. Default value is 'native'")
            sys.exit(1)
    oformat = args.output

    retval = 0
    try:
        flist = glob.glob(crspath)
        flist.sort()
    except:
        errmsg("Can't open files in given path!")
        sys.exit(1)

    if len(flist) == 0:
        errmsg("List of files is empty!")
        sys.exit(1)

    for f in flist:
        try:
            with open(f, 'r') as inputfile:
                data = inputfile.read()
        except:
            errmsg("Can't open file: %s" % f)
            sys.exit(1)

        ### check file syntax
        msg("Config file: %s" % (f))
        try:
            mparser = msc_pyparser.MSCParser()
            mparser.parser.parse(data)
            msg(" Parsing ok.")
        except:
            errmsg("Can't parse config file: %s" % (f))
            sys.exit(1)

        c = Check(mparser.configlines)

        ### check case usings
        c.check_ignore_case()
        if len(c.caseerror) == 0:
            msg(" Ignore case check ok.")
        else:
            errmsg(" Ignore case check found error(s)")
            for a in c.caseerror:
                errmsg("    In file: %s - %s" % (f, a))
                retval = 1

        ### check action's order
        c.check_action_order()
        if len(c.orderacts) == 0:
            msg(" Action order check ok.")
        else:
            errmsg(" Action order check found error(s)")
            for a in c.orderacts:
                errmsg("    In file: %s - rule ID: {}, action '{}' at pos {} is wrong place against '{}' at pos {}".format(*a) % (f))
                retval = 1

        ### make a diff to check the indentations
        try:
            with open(f, 'r') as fp:
                fromlines = fp.readlines()
        except:
            errmsg("  Can't open file for indent check: %s" % (f))
            retval = 1
        # virtual output
        mwriter = msc_pyparser.MSCWriter(mparser.configlines)
        mwriter.generate()
        #mwriter.output.append("")
        output = []
        for l in mwriter.output:
            if l == "\n":
                output.append("\n")
            else:
                output += [l + "\n" for l in l.split("\n")]
        
        diff = difflib.unified_diff(fromlines, output)
        if fromlines == output:
            msg(" Indentation check ok.")
        else:
            errmsg(" Indentation check found error(s)")
            retval = 1
        for d in diff:
            errmsg(d.strip("\n"))

    sys.exit(retval)