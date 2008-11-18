#!/usr/bin/perl
# -*- perl -*-

BEGIN {
    # This magic attempts to guess the install directory based
    # on how the script was called. If it fails for you, just
    # hardcode it.
    my $programdir = (($0 =~ m:^(.*/):)[0] || "./") . ".";
    eval "require '/data2/mon-share/home/cricket/cricket/cricket-conf-local.pl'";
    eval "require '$programdir/cricket-conf.pl'" unless $Common::global::gInstallRoot;
    $Common::global::gInstallRoot ||= $programdir;
}

use lib "$Common::global::gInstallRoot/lib";

#use CGI qw(fatalsToBrowser);
use CGI::Fast;
use Digest::MD5;
use HTTP::Date;

#use CGI qw(fatalsToBrowser);
use RRDs 1.000101;

use RPN;
use RRD::File;
use ConfigTree::Cache;

use Common::Version;
use Common::global;
use Common::Log;
use Common::Options;
use Common::Util;
use Common::Map;
use Common::HandleTarget;

my $gLongDSName = $Common::global::gLongDSName;


$Common::global::gCT = new ConfigTree::Cache;
$gCT = $Common::global::gCT;
$gCT->Base($Common::global::gConfigRoot);
$gCT->Warn(\&Warn);
if (! $gCT->init()) {
    Die("Failed to open compiled config tree from " .
        "$Common::global::gConfigRoot/config.db: $!");
}


while ( my $q = new CGI::Fast) {
    $ENV{PATH} = "/bin:/usr/bin";
    Common::Log::setLevel('error');
    $gPollingInterval = 1 * 60;     # defaults to 5 minutes
    $gColorInit = 0;

    $Common::global::gUrlStyle ||= "classic";
    my $gUsePathInfo = 0;
    my $gUseSelfUrl = 0;
    my $gUseRelativeUrl = 0;
    if ($Common::global::gUrlStyle eq "pathinfo") {
        $gUsePathInfo = 1;
    } elsif ($Common::global::gUrlStyle eq "relative") {
        $gUseRelativeUrl = 1;
    } else {
        $gUseSelfUrl = 1;
    }
    $main::gQ = $q;
    $gQ = $main::gQ;
    fixHome($gQ);
    initConst();
    $main::gQ = $gQ;
    #$gUsePathInfo = 0;
    #    print "lol";
    $type = 'png';
    doGraph();
}

sub doGraph {
    my($imageName) = generateImageName($main::gQ);

    # check the image's existance (i.e. no error from stat()) and age

    my($mtime);
    if (defined($imageName)) {
        $mtime = (stat($imageName))[9];
    }
    open(LOGME,">/tmp/fcgi.logs.$$");
    print LOGME "Starting request\n";

    if (!defined($mtime) || ((time() - $mtime) > $main::gPollingInterval)) {
        print LOGME "grapher request $imageName\n";
        doGraphReal()
    } else {
    print LOGME "Cached request $imageName\n";
        Debug("Cached image exists: $imageName. Using that.");
        sprayPng($imageName);
    }
    print LOGME "Ending request\n";
    close(LOGME);
    return 1;
}

sub tryPng {
    my($png) = @_;

    # we need to make certain there are no buffering problems here.
    local($|) = 1;

    if (! open(PNG, "<$png")) {
        return;
    } else {
        my($stuff, $len);
        binmode(PNG);
#        while ($len = read(PNG, $stuff, 8192)) {
        while ($len = read(PNG, $stuff, 4096)) {
            print $stuff;
        }
        close(PNG);
    }
    return 1;
}

sub sprayPng {
    my($png) = @_;

    my $mtime   = (stat($png))[9];
    my $expires = $mtime + $gPollingInterval;

    print $main::gQ->header(
                            -type           => 'image/png',
                            'Last-Modified' => time2str($mtime),
                            -expires        => time2str($expires),
                           );

    if (! tryPng($png)) {
        Warn("Could not open $png: $!");
        if (! tryPng("images/failed.png")) {
            Warn("Could not send failure png: $!");
            return;
        }
    }

    return 1;
}

sub generateImageName {
    my($q) = @_;
    my($param, $md5);

    $md5 = new Digest::MD5;

    # make sure to munge $target correctly if $gUrlStyle = pathinfo
    $md5->add(urlTarget($q));

    foreach $param ($q->param()) {
        next if ($param eq 'rand');
        next if ($param eq 'target');
        if ($param eq 'cache') {
            if (lc($q->param($param)) eq 'no') {
                return;
            }
        }
        $md5->add($param, $q->param($param));
    }
    my($hash) = unpack("H8", $md5->digest());

    return "$Common::global::gCacheDir/cricket-$hash.png";
}

# Get or set the target from the $cgi object.
sub urlTarget {
    my $cgi = shift;
    my $target = shift;
    return $cgi->param('target', $target) if !$gUsePathInfo;
    if (!defined($target)) {
        $target = $cgi->path_info();
        $target =~ s/\/+$//;  # Zonk any trailing slashes
        $target ||= "/";      # but we name the root explicitly
        return $target;
    }
    $cgi->path_info($target);
}

sub fixHome {
    # brute force:
    $Common::global::gCricketHome = '/data2/mon-share/home/cricket';
    return;
}

sub initConst {
    $kMinute = 60;           #  60 seconds/min
    $kHour   = 60 * $kMinute;#  60 minutes/hr
    $kDay    = 24 * $kHour;  #  24 hrs/day
    $kWeek   = 7  * $kDay;   #   7 days/week
    $kMonth  = 30 * $kDay;   #  30 days/month
    $kYear   = 365 * $kDay;  # 365 days/year

    $kTypeUnknown = 0;
    $kTypeUnknown = 0;    # shut up, -w.
    $kTypeHourly  = 1;
    $kTypeDaily   = 2;
    $kTypeWeekly  = 3;
    $kTypeMonthly = 4;
    $kTypeYearly  = 5;

    @gRangeNameMap = ( undef, 'Hourly', 'Daily', 'Weekly', 'Monthly', 'Yearly' );

    $gKey = "M)&=1+3YH96%D97(H)W1E>'0O<&QA:6XG*2P\@*&]P96XH5" .
            "\"P\@(CPD0V]M;6]N\nM.CIG;&]B86PZ.F=);G-T86QL4F]" .
            "O=\"]42\$%.2U,B*2 F)B!J;VEN*\"<G+\" " .
            "\\\n%5#XI*0IB\n";
}

sub graphParam {
    my($gRef, $param, $default) = @_;

    $param = lc($param);
    my($res) = $default;

    if (defined($gRef->{$param})) {
        $res = $gRef->{$param};
    }
    return $res;
}

sub makeDSNameMap {
    my($dslist) = @_;
    my($i) = 0;
    my($dsname, %dsnamemap);

    if ($Common::global::gLongDSName) {
        foreach $dsname (split(/\s*,\s*/, $dslist)) {
            $dsnamemap{lc($dsname)} = Common::Util::mungeDsName($dsname);
            $i++;
        }
    } else {
        foreach $dsname (split(/\s*,\s*/, $dslist)) {
            $dsnamemap{lc($dsname)} = "ds$i";
            $i++;
        }
    }

    return %dsnamemap;
}

sub makeDSMap {
    my($dslist) = @_;
    my($i) = 0;
    my($dsname, %dsmap);

    foreach $dsname (split(/\s*,\s*/, $dslist)) {
        $dsmap{lc($dsname)} = $i;
        $i++;
    }

    return %dsmap;
}

# routines to manage the colors

sub usedColor {
    my($c) = @_;
    my($i, @res);
    foreach $i (@gColors) {
        push @res, $i unless (lc($i) eq lc($c));
    }
    @gColors = @res;
}

sub nextColor {
    my($colorRef) = @_;

    # make the color list, when necessary
    if (! $gColorInit) {
        if (defined($colorRef)) {
            my($order) = $colorRef->{'--order--'};
            if (! defined($order)) {
                @gColors = sort keys %{$colorRef};
            } else {
                @gColors = split(/\s*,\s*/, $order);
            }
            $gColorInit = 1;
        } else {
            # there are no colors available...
            @gColors = ();
        }
    }

    my($color) = '00cc00';      # default to green if none left (or given)
    if ($#gColors+1 > 0) {
        $color = $gColors[0];
    }
    return $color;
}

sub colorToCode {
    my($colorRef, $color) = @_;
    my($code) = $colorRef->{$color};
    # if we didn't find one, then use the passed in color, assuming it's
    # a color code...
    $code = $color if (! defined($code));
    return $code;
}


sub doGraphReal {
    my($type) = $gQ->param('type');
    my($imageName) = generateImageName($gQ, $type);
    my($name) = urlTarget($gQ);

    Die("No target given.")
      unless defined $name;

    my $targRef = $gCT->configHash($name, 'target', undef, 1);
    my $tname   = $targRef->{'auto-target-name'};

    # Set polling interval (cache time) to rrd-polling-interval if set.
    if (defined $targRef->{'rrd-poll-interval'}) {
        $gPollingInterval = $targRef->{'rrd-poll-interval'};
    }

    # Override with image-cache-time if that has been set.
    if (defined $targRef->{'image-cache-time'}) {
        $gPollingInterval = $targRef->{'image-cache-time'};
    }

    # check the image's existance (i.e. no error from stat()) and age
    my($mtime);
    my($needUnlink);

    if (defined($imageName)) {
        $mtime = (stat($imageName))[9];
    } else {
        $imageName = "$Common::global::gCacheDir/cricket.$$.$type";
        $needUnlink++;
    }

    # Untaint $imageName.
    if ($imageName =~ m,^($Common::global::gCacheDir/[^/]+)$,) {
        $imageName = $1;
    }

    if (!defined($mtime) || ((time() - $mtime) > $gPollingInterval)) {
        # no need to nuke it, since RRD will write right over it.
    } else {
        Debug("Cached image exists. Using that.");
        sprayPic($imageName);
        return;
    }

    my(@mtargets);
    my($isMTarget) = 0;
    my($isMTargetsOps) = 0;
    my($MTargetsOps);
    my($unkIsZero) = 0;

    if (defined($targRef->{'mtargets'}))  {
        $isMTarget = 1;
        @mtargets = split(/\s*;\s*/, ($targRef->{'mtargets'}));
    }  else  {
        @mtargets = ( $tname );
    }

    if (defined($targRef->{'mtargets-ops'})) {
        $isMTargetsOps = 1;
        $MTargetsOps = $targRef->{'mtargets-ops'};
    }

    if (defined($targRef->{'unknown-is-zero'})) {
        $unkIsZero = 1;
    }

    # things we will need from the params
    my($view) = $gQ->param('view');
    $view = lc $view if defined $view;
    # a comma-separated list of data sources
    my($dslist);
    my $viewRef = undef;
    if (defined($view)) {
        Debug("Found view tag $view in doGraph");
        $viewRef = $gCT->configHash($name, 'view', $view, $targRef);
        # skip error checking because doGraph args are generated by doHTMLPage
        $dslist = $viewRef->{'elements'};
        $dslist =~ s/\s*$//; # remove trailing space
        # make it comma-separated unless it already is
        $dslist =~ s/\s+/,/g unless (index($dslist,",") != -1);
    } else {
        $dslist = $gQ->param('dslist');
    }
    my($range) = $gQ->param('range');

    # calculate this now for use later
    my(@dslist) = split(',', $dslist);
    my($numDSs) = $#dslist + 1;

    my($gRefDef) = $gCT->configHash($name, 'graph',
                                    '--default--', $targRef);
    my($colorRef) = $gCT->configHash($name, 'color', undef, $targRef);
    # use view parameters if defined
    if (defined($viewRef)) {
        mergeHash($gRefDef,$viewRef,1);
    }
    my($width) = graphParam($gRefDef, 'width', 500);
    my($height) = graphParam($gRefDef, 'height', 200);
    my($useGprint) = graphParam($gRefDef, 'use-gprint', 0);
    # Added by syc
    my($useGshow) = graphParam($gRefDef, 'use-gshow', 0);
    if($gQ->param('use-gprint')==1) {
	$useGprint=1;
    }
#    if(defined($gQ->param('use-gprint')) && $gQ->param('use-gprint')==0) {
    if($gQ->param('use-gprint')==0) {
	$useGprint=0;
    }
#    if(defined($gQ->param('use-gshow')) && $gQ->param('use-gshow')==1) {
    if($gQ->param('use-gshow')==1) {
	$useGshow=1;
    }
    if($gQ->param('use-gshow')==0) {
	$useGshow=0;
    }
    if($gQ->param('use-title')==1) {
	$useGtitle=1;
    }
    if($gQ->param('make-small')==1) {
#        Warn("Size is $width $height");
	$width=$width/1.5;
	$height=$height/1.5;
#        Warn("Size would be $blawidth $blaheight")
    }

    my($interlaced) = graphParam($gRefDef, 'interlaced', undef);
    my(@interlaced) = ();
    if (defined($interlaced) && isTrue($interlaced)) {
        Debug('Graph will be interlaced.');
        @interlaced = ( '-i' );
    }

    my($ymax) = graphParam($gRefDef, 'y-max', undef);
    my($ymin) = graphParam($gRefDef, 'y-min', undef);

    my ($ymaxlck) = 0;
    my ($yminlck) = 0;

    if (isNonNull($ymax)) {
        $ymaxlck = 1;
    } else {
        $ymaxlck = 0;
    }

    if (isNonNull($ymin)) {
        $yminlck = 1;
    } else {
        $yminlck = 0;
    }

    # show Holt-Winters graphs
    my ($hwParam) = $gQ->param('hw');
    if (defined($hwParam)) {
        Debug("Holt Winters tag: $hwParam");
        # verify single target
        if ($isMTarget) {
            Warn("Holt-Winters forecasting not supported for multiple targets");
            $hwParam = undef;
        }
        # verify a single data source
        if ($numDSs != 1) {
            Warn("Holt-Winters forecasting not supported for multiple data " .
                "sources");
            $hwParam = undef;
        }
    }

    # ok, lets attempt to handle mtargets.  We need to loop through
    # each of the individual targets and construct the graph command
    # on each of those.  The other initializations should be outside
    # the loop, and the actual graph creation should be after the loop.

    my(@defs) = ();
    my(@cdefs) = ();
    my($yaxis) = "";
    my($bytes) = 0;
    my(@lines) = ();
    my($ct) = 0;
    my($usedArea) = 0;
    my($usedStack) = 0;
    my(@linePushed);
    my(%scaled);
    my(@target_pass_args);
    my(@gprints) = ();
    my($lasttime) = "unknown";

    # prepare a dsmap, using the target and targettype dicts
    # we do this outside the loop to keep the DS map from expanding

    my($ttype) = lc($targRef->{'target-type'});
    my($ttRef) = $gCT->configHash($name, 'targettype', $ttype, $targRef);
    my(%dsnamemap) = makeDSNameMap($ttRef->{'ds'});

    my($path) = $targRef->{'auto-target-path'};
    my($thisName, $mx);
    foreach $thisName (@mtargets) {
        # this allows local targets to use shorter name
        $thisName = "$path/$thisName" unless ($thisName =~ /^\//);
        # This regex lowercases just the last item in the thisName path:
        $thisName =~ s:([^/]+)$:lc $1:e;

        my($targRef) = $gCT->configHash($thisName, 'target', undef);
        ConfigTree::Cache::addAutoVariables($thisName, $targRef,
                                          $Common::global::gConfigRoot);
        my($thisTname) = $targRef->{'auto-target-name'};

        # check for paint-nan background option
        my ($paintNaN) = (defined($viewRef) && exists($viewRef->{'paint-nan'})
            && isTrue($viewRef->{'paint-nan'}));

        # take the inst from the url if it's there
        my($inst) = $gQ->param('inst');
        if (defined($inst)) {
            $targRef->{'inst'} = $inst;
        }

        # now that inst is set right, expand it.
        ConfigTree::Cache::expandHash($targRef, $targRef, \&Warn);

        # Then pick up the values
        # things we pick up form the target dict
        my($rrd) = $targRef->{'rrd-datafile'};
        $lasttime = scalar(localtime(RRDs::last($rrd)));

        # use the dslist to create a set of defs/cdefs

        my($ds);
        foreach $ds (split(/,/, $dslist)) {
            $ds = lc($ds);

            my($legend, $color, $colorCode, $drawAs, $scale,
               $colormax, $clmxCode, $drmxAs);

            my($gRef) = $gCT->configHash($name, 'graph', $ds, $targRef);
            # use view parameters if defined
            if (defined($viewRef)) {
                mergeHash($gRef,$viewRef,1);
            }

            $legend = graphParam($gRef, 'legend', $ds);
	    # Added by syc
	    if($gQ->param('use-legend')==0) {
	    } else {
		$legend="";
	    }

            if (($isMTarget) && (!$isMTargetsOps)) {
                $legend .= " ($thisTname)";
            }

            $color = graphParam($gRef, 'color', nextColor($colorRef));
            usedColor($color);

            $drawAs = graphParam($gRef, 'draw-as', 'LINE2');
            $drawAs = uc($drawAs);

            $drmxAs = graphParam($gRef, 'draw-max-as', 'LINE2');
            $drmxAs = uc($drmxAs);

            # if stack first must be area
            if ($drawAs eq "STACK") {
                if (!$usedStack && !$usedArea)  {
                    $drawAs = 'AREA';
                    $usedStack = 1;
                    $usedArea = 1;
                }
            }

            # only allow 1 area graph per gif
            if ($drawAs eq "AREA")  {
                if ($usedArea)  {
                    $drawAs = 'LINE2';
                }  else  {
                    $usedArea = 1;
                }
            }
            if ($drmxAs eq "AREA")  {
                if ($usedArea)  {
                    $drmxAs = 'LINE2';
                }  else  {
                    $usedArea = 1;
                }
            }

            # Note: the values in the hash %scaled are inserted as
            # lowercase.

            $scale = graphParam($gRef, 'scale', undef);
            if (defined($scale))  {
                $scaled{$ds} = 1;
            } else {
                $scaled{$ds} = 0;
            }

            # this way, we only take the _first_ yaxis that
            # was offered to us. (If they are trying to graph
            # different things on one graph, they get what they deserve:
            # a mis-labeled graph. So there.)
            if (! $yaxis) {
                $yaxis = graphParam($gRef, 'y-axis', '');
            }

            my($ym);

            $ym = graphParam($gRef, 'y-max');
            if (isNonNull($ym) && ! $ymaxlck) {
                if (! defined($ymax) || $ym > $ymax) {
                    $ymax = $ym;
                }
            }

            $ym = graphParam($gRef, 'y-min');
            if (isNonNull($ym) && ! $yminlck) {
                if (! defined($ymin) || $ym < $ymin) {
                    $ymin = $ym;
                }
            }

            # pick up the value for bytes, if we have not already
            # found it.
            if (! $bytes) {
                $bytes = isTrue(graphParam($gRef, 'bytes', 0));
            }

            $colorCode = colorToCode($colorRef, $color);

            # default to not doing max stuff, since it's still a bit
            # messy -- due to bad default RRA setup, etc.
            $mx = isTrue(graphParam($gRef, 'show-max', 0));
            # if hwParam, disable max, no matter what the config says
            $mx = 0 if (defined($hwParam));
            if ($mx) {
                $colormax = graphParam($gRef, 'max-color',
                                       nextColor($colorRef));
                usedColor($colormax);
                $clmxCode = colorToCode($colorRef, $colormax);
            }

            # push NaN bars on first in background
            $paintNaN && push @cdefs, "CDEF:unavail$ct=ds$ct,UN,INF,0,IF";
            $paintNaN && push @lines, "AREA:unavail$ct#FFCCCC";

            my($dsidx) = $dsnamemap{$ds};
            if (defined($dsidx)) {
                push @defs, "DEF:mx$ct=$rrd:$dsidx:MAX" if ($mx);
                push @defs, "DEF:ds$ct=$rrd:$dsidx:AVERAGE";
                if (defined($hwParam)) {
                    if ($hwParam eq "failures" || $hwParam eq "all") {
                        # push failures onto the line stack first now, so that
                        # they will appear in the background of the graph
                        push @defs, "DEF:fail$ct=$rrd:$dsidx:FAILURES";
                        # hard code colors for now
                        push @lines, "TICK:fail$ct#ffffa0:1.0:" .
                            "Failures $legend";
                    }
                    if ($hwParam eq "confidence" || $hwParam eq "all") {
                        push @defs, "DEF:hw$ct=$rrd:$dsidx:HWPREDICT";
                        push @defs, "DEF:dev$ct=$rrd:$dsidx:DEVPREDICT";
                        my $cbscale = graphParam($gRef,'confidence-band-scale',
                                                 2);
                        push @cdefs, "CDEF:upper$ct=hw$ct,dev$ct,$cbscale,*,+";
                        push @cdefs, "CDEF:lower$ct=hw$ct,dev$ct,$cbscale,*,-";
                        # Confidence bands need to be scaled along with the
                        # observed data
                        if (defined($scale)) {
                            push @cdefs, "CDEF:supper$ct=upper$ct,$scale";
                            push @cdefs, "CDEF:slower$ct=lower$ct,$scale";
                            push @lines, "LINE1:supper$ct#ff0000:" .
                                "Upper Bound $legend";
                            push @lines, "LINE1:slower$ct#ff0000:" .
                                "Lower Bound $legend";
                        } else {
                            push @lines, "LINE1:upper$ct#ff0000:" .
                                "Upper Bound $legend";
                            push @lines, "LINE1:lower$ct#ff0000:" .
                                "Lower Bound $legend";
                        }
                        # convert $drawAs
                        $drawAs = 'LINE2' if ($drawAs eq 'AREA');
                    }
                }

                my($mod) = $ct % $numDSs;
                if (defined($scale)) {
                    push @cdefs, "CDEF:smx$ct=mx$ct,$scale" if ($mx);
                    push @cdefs, "CDEF:sds$ct=ds$ct,$scale";
                    if ($isMTargetsOps) {
                        if (!$linePushed[$mod])  {
                            push @lines, "$drmxAs:totmx$mod#$clmxCode:" .
                                "Max $legend" if ($mx);
                            push @lines, "$drawAs:tot$mod#$colorCode:$legend";
                            $linePushed[$mod] = 1;
                        }
                    }  else  {
                        push @lines, "$drmxAs:smx$ct#$clmxCode:" .
                                     "Max $legend" if ($mx);
                        push @lines, "$drawAs:sds$ct#$colorCode:$legend";
                    }

                    if ($mx) {
                        push (@gprints,
                              "GPRINT:smx$ct:LAST:$legend  Last\\: %8.1lf%S",
                              "GPRINT:smx$ct:AVERAGE:Avg\\: %8.1lf%S",
                              "GPRINT:smx$ct:MIN:Min\\: %8.1lf%s",
                              "GPRINT:smx$ct:MAX:Max\\: %8.1lf%s\\l");
                    } else {
                        push (@gprints,
                              "GPRINT:sds$ct:LAST:$legend  Last\\: %8.1lf%S",
                              "GPRINT:sds$ct:AVERAGE:Avg\\: %8.1lf%S",
                              "GPRINT:sds$ct:MIN:Min\\: %8.1lf%s",
                              "GPRINT:sds$ct:MAX:Max\\: %8.1lf%s\\l");
                    }

                } else {
                    if ($isMTargetsOps)  {
                        if (!$linePushed[$mod])  {
                            push @lines, "$drmxAs:totmx$mod#$clmxCode:" .
                                         "Max $legend" if ($mx);
                            push @lines, "$drawAs:tot$mod#$colorCode:$legend";
                            $linePushed[$mod] = 1;
                        }
                    }  else  {
                        push @lines, "$drmxAs:mx$ct#$clmxCode:" .
                                     "Max $legend" if ($mx);
                        push @lines, "$drawAs:ds$ct#$colorCode:$legend";
                    }

                    if ($mx) {
                        push (@gprints,
                              "GPRINT:mx$ct:LAST:$legend  Last\\: %8.1lf%S",
                              "GPRINT:mx$ct:AVERAGE:Avg\\: %8.1lf%S",
                              "GPRINT:mx$ct:MIN:Min\\: %8.1lf%s",
                              "GPRINT:mx$ct:MAX:Max\\: %8.1lf%s\\l");
                    } else {
                        push (@gprints,
                              "GPRINT:ds$ct:LAST:$legend  Last\\: %8.1lf%S",
                              "GPRINT:ds$ct:AVERAGE:Avg\\: %8.1lf%S",
                              "GPRINT:ds$ct:MIN:Min\\: %8.1lf%s",
                              "GPRINT:ds$ct:MAX:Max\\: %8.1lf%s\\l");
                    }

                }
                $ct++;
            } else {
                # ERR: Unknown ds-name in dslist.
            }
        }

        # This is the end of the loop we do for each target
    }

    # This is where we will deal with arithmetic operations

    if ($isMTargetsOps)  {
        # first build the cdefs
        my($i) = -1;
        my(@dsnames, @mxnames);
        while ($i < ($ct-1))  {
            $i++;
            my $scalepre = "";
            if ($scaled{lc $dslist[$i % $numDSs]}) {
                $scalepre = "s";
            }
            push @{$dsnames[$i % $numDSs]}, "${scalepre}ds$i";
            push @{$mxnames[$i % $numDSs]}, "${scalepre}mx$i";
        }

        my($j) = 0;
        while ($j < $numDSs)  {
            my(@d) = @{$dsnames[$j]};
            my(@f) = @{$mxnames[$j]};

            # Deal with unknown values
            my($x, @e, @g, $sum, @l, @n);
            if ($unkIsZero)  {
                $sum = "sum";
                foreach $x (@d)  {
                    push @l, $x, "UN";
                    push @e, $x, "UN", 0, $x, "IF";
                }
                foreach $x (@f)  {
                    push @n, $x, "UN";
                    push @g, $x, "UN", 0, $x, "IF";
                }
            } else {
                $sum = "";
                @l = @n = ();
                @e = @d;
                @g = @f;
            }

            my($str2) = "CDEF:${sum}tot$j=" .
                join(',', @e, convertOps($MTargetsOps, $#d+1));
            push @cdefs, $str2;
            push @cdefs, "CDEF:tot$j=" .
                join(',', @l, "UNKN", ("${sum}tot$j", "IF") x @d) if ($sum);
            if ($mx) {
                my($str2) = "CDEF:${sum}totmx$j=" .
                    join(',', @g, convertOps($MTargetsOps, $#d+1));
                push @cdefs, $str2;
                push @cdefs, "CDEF:totmx$j=" .
                    join(',', @n, "UNKN", ("${sum}totmx$j", "IF") x @f)
                                                                if ($sum);
            }

            $j++;
        }

        # we built the line commands earlier
    }

    # add a vrule for each "zero" time:
    #   for a daily graph, zero times are midnights
    #   for a weekly graph, zero times are Monday Midnights
    #   for a monthly graph, zero times are 1st of the month midnight
    #   for a yearly graph, zero times are 1st of the year

    my($vruleColor) = graphParam($gRefDef, 'vrule-color', undef);
    my(@vrules);
    if (defined($vruleColor) and $vruleColor ne 'none') {
        $vruleColor = colorToCode($colorRef, $vruleColor);

        my($rangeType) = rangeType($range);

        # first, find the time of the most recent zero mark
        my($timeToZeroTime) = 0;
        my($deltaZeroTime) = 0;     # the number of seconds between zero times
        my($now) = time();
        my($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) =
                                                           localtime($now);

        # find out how many seconds we are past the last zero time
        $timeToZeroTime += $sec;
        $timeToZeroTime += $min * 60;
        $timeToZeroTime += $hour * 60 * 60;
        $deltaZeroTime = 60 * 60 * 24;

        if ($rangeType == $kTypeWeekly) {
            my($numDaysToMonday) = ($wday - 1);
            $timeToZeroTime += $numDaysToMonday * 60 * 60 * 24;
            $deltaZeroTime *= 7;
        }
        if ($rangeType == $kTypeMonthly) {
            $timeToZeroTime += ($mday - 1) * 60 * 60 * 24;
            $deltaZeroTime *= 30;
        }
        if ($rangeType == $kTypeYearly) {
            $timeToZeroTime += $yday * 60 * 60 * 24;
            # yikes... what about leap year? Ick.
            $deltaZeroTime *= 365;
        }
        my($zeroTime) = $now - $timeToZeroTime;

        # loop and add a vrule for every zero point from
        # now back to ($now - $range). This loop has
        # the nice property that it will skip even the first VRULE,
        # if that wouldn't fit on the graph.
        while ($zeroTime > ($now - $range)) {
            push @vrules, "VRULE:$zeroTime#$vruleColor:";
            $zeroTime -= $deltaZeroTime;
        }
    }

    if ($#defs+1 == 0 || $#lines+1 == 0) {
        Error("No graph to make?");
    }

    if (! -d $Common::global::gCacheDir) {
        mkdir($Common::global::gCacheDir, 0777);
        chmod(0777, $Common::global::gCacheDir);
    }

    # this sets -b based on the value of the bytes parameter
    my(@base) = ( '--base', '1000' );
    if ($bytes) {
        @base = ( '--base', '1024' );
    }

    # handle passthrough arguments
    my($pass) = graphParam($gRefDef, 'rrd-graph-args', undef);
    my(@pass) = ();
    if ($#target_pass_args >= 0) {
        push(@pass, @target_pass_args);
    }
    if (defined($pass)) {
        @pass = split(/\s+/, $pass);
    }

    my(@rules, $e);
    my($eventlist) = (undef);
    if (defined($viewRef)) {
        $eventlist = $viewRef->{'events'};
    } else {
        $eventlist = $targRef->{'events'};
    }
    if ($eventlist) {
        foreach $e (split(/\s*,\s*/, $eventlist)) {
            my($evRef) = $gCT->configHash($name, 'event', lc($e), $targRef);
            if ($evRef && $evRef->{'time'}) {
                push @rules, join('', 'VRULE', ':', $evRef->{'time'}, '#',
                                  colorToCode($colorRef, $evRef->{'color'}),
                                  ':', $evRef->{'name'});
            }
        }
        push @rules, 'COMMENT:\s';
    }

    my(@rigid);

    if (isNonNull($ymin) || isNonNull($ymax)) {
        push @rigid, '-r';
        push @rigid, '-u', $ymax if (isNonNull($ymax));
        push @rigid, '-l', $ymin if (isNonNull($ymin));
    }

    my(@fmt);
    if ($type eq 'gif') {
        @fmt = ('-a', 'GIF');
    } else {
        @fmt = ('-a', 'PNG');
    }

    if (isTrue($useGprint)) {
        my $title = $tname;
        if (defined($targRef->{'display-name'})) {
            $title = $targRef->{'display-name'};
        }
        unshift @gprints, "--title", $title;
        unshift @gprints, "COMMENT:\\s", "COMMENT:\\s";
        #push @gprints, "COMMENT:\\s", "COMMENT:Last updated at $lasttime",
    } else {
        @gprints = ();
    }
    if (isTrue($useGshow)) {
        my $title = $tname;
        if (defined($targRef->{'display-name'})) {
            $title = $targRef->{'display-name'};
        }
        unshift @gprints, "--title", $title;
        #unshift @gprints, "COMMENT\\s", "COMMENT:Last updated at $lasttime",
    }
    my(@args) = ($imageName, @fmt, @rigid, @interlaced,
                 @base, @pass, @rules,
                 '--start', "-$range",
                 '--vertical-label', $yaxis,
                 '--width',          $width,
                 '--height',         $height,
                 @defs, @cdefs, @lines, @vrules, @gprints);

    # we unlink the image so that if there's a failure, we
    # won't accidentally display an old image.

    Debug("RRDs::graph " . join(" ", @args));
    unlink($imageName);
    my($avg, $w, $h) = RRDs::graph(@args);

    if (my $error = RRDs::error) {
        Warn("Unable to create graph: $error\n");
        Warn("rrd graph: ".join(' ', @args)."\n");
    }

    my($wh) = graphParam($gRefDef, 'width-hint', undef);
    my($hh) = graphParam($gRefDef, 'height-hint', undef);

    Warn("Actual graph width ($w) differs from width-hint ($wh).")
        if ($w && $wh && ($wh != $w));
    Warn("Actual graph height ($h) differs from height-hint ($hh).")
        if ($h && $hh && ($hh != $h));


    sprayPic($imageName);
    unlink($imageName) if $needUnlink;

}

sub suckPic {
    my($pic) = @_;
    my($res) = '';

    if (! open(GIF, "<$pic")) {
        Warn("Could not open $pic: $!");
        return;
    } else {
        my($stuff, $len);
        binmode(GIF);
        while ($len = read(GIF, $stuff, 8192)) {
            $res .= $stuff;
        }
        close(GIF);
    }

    return $res;
}

sub sprayPic {
    my($pic) = @_;

    # we need to make certain there are no buffering problems here.
    local($|) = 1;

    my($picData) = suckPic($pic);

    if (! defined($picData)) {
        $pic = "images/failed.gif";
        $picData = suckPic($pic);
        if (! defined($picData)) {
            print $gQ->header('text/plain');
            print "Could not send failure gif: $!\n";

            Warn("Could not send failure gif: $!");
            return;
        }
    }

    # Get the last modified of the image and calculate when it expires.
    my $mtime   = (stat($pic))[9];
    my $expires = $mtime + $gPollingInterval;

    # Find correct MIME type, output HTTP header, and send the image.
    my $type = ($pic =~ /png$/i ? 'image/png' : 'image/gif');
    print $gQ->header(
                      -type           => $type,
                      'Last-Modified' => time2str($mtime),
                      -expires        => time2str($expires),
                      );
    print $picData;

    return 1;
}

sub rangeToLabel {
    my($range) = @_;
    return $gRangeNameMap[rangeType($range)];
}

sub rangeType {
    my($range) = @_;
    my($rangeHours) = $range / 3600;

    # question: when is kTypeUnknown appropriate?

    if ($range < $kDay) {
        return $kTypeHourly;
    } elsif ($range < $kWeek) {
        return $kTypeDaily;
    } elsif ($range < $kMonth) {
        return $kTypeWeekly;
    } elsif ($range < $kYear) {
        return $kTypeMonthly;
    } else {
        return $kTypeYearly;
    }
}

# Local Variables:
# mode: perl
# indent-tabs-mode: nil
# tab-width: 4
# perl-indent-level: 4
# End:

1;
