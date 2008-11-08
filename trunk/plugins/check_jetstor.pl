#!/usr/bin/perl -w
#
# check_jetstor
#   Nagios script to check JetStor arrays via snmp (known to work with
#   416F, 516F and 416iS).  This script was inspired by Karl Katzke's
#   check_jetstor_snmp script.
#
# Copyright (c) 2008 David Alden <alden@math.ohio-state.edu>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#
# Description:
#   This script will check the status of several different JetStor
# raid systems (currently 416F, 516F and 416iS)
#
#
# Installation:
#   Edit this script, replacing the line:
#       use lib "/usr/lib/nagios/plugins";
#   with the path to your nagios plugins directory (where utils.pm is
#   located).  Then copy the script into your nagios plugins directory.
#
#

use strict;
use SNMP;
use Getopt::Long;
use lib "/usr/local/nagios/libexec";
use utils qw(%ERRORS &print_revision &support &usage);

#
my $snmpPort = 161;
my $snmpVersion = "2c";
my $snmpTimeout = "30000000";  # The Jetstor occasionally takes a little while to respond 

#
my %oids = (
            checkFiber => '.1.3.6.1.4.1.14752.1.2.1.2.0',
            checkiSCSI => '.1.3.6.1.4.1.22274.1.1.1',
#
            fiberPSStatuses => '.1.3.6.1.4.1.14752.1.2.2.12.1.2',
            fiberFanSpeeds => '.1.3.6.1.4.1.14752.1.2.2.13.1.2',
            fiberHDDTemps => '.1.3.6.1.4.1.14752.1.2.2.14.1.2',
            fiberVolumeNames => '.1.3.6.1.4.1.14752.1.2.5.1.1.2',
            fiberVolumeStatuses => '.1.3.6.1.4.1.14752.1.2.5.1.1.5',
#
            iSCSIudvNames => '.1.3.6.1.4.1.22274.1.2.3.1.2',
            iSCSIudvStatuses => '.1.3.6.1.4.1.22274.1.2.3.1.3',
            iSCSIemsNames => '.1.3.6.1.4.1.22274.1.3.2.1.1',
            iSCSIpsuStatus => '.1.3.6.1.4.1.22274.1.3.2.1.2',
            iSCSIfanStatus => '.1.3.6.1.4.1.22274.1.3.2.1.2',
           );

#
my $PROGNAME="check_jetstor";
my $REVISION="0.9";

#
#$ENV{PATH}="/usr/sbin:/usr/bin:/bin";

#
my $community = "public";
my $help;
my $hostname;
my $timeout = 360;        # multiple snmp gets on 416iS can take a long time
my $version;

if (GetOptions(
               "C:s" => \$community,  "community"  => \$community,
                                      "help"       => \$help,
               "H:s" => \$hostname,   "hostname:s" => \$hostname,
               "t=i" => \$timeout,    "timeout=i"  => \$timeout,
               "V"   => \$version,    "Version"    => \$version,
              ) == 0) {
  print_usage();
  exit $ERRORS{'UNKNOWN'};
}

if ($version) {
  print_revision($PROGNAME, "\$Revision: $REVISION \$");
  exit $ERRORS{'OK'};
}

if ($help) {
  print_help();
  exit $ERRORS{'OK'};
}

if (! utils::is_hostname($hostname)) {
  print_usage();
  exit $ERRORS{'UNKNOWN'};
}

$SIG{'ALRM'} = sub {
        print "Timeout: No Answer from Client\n";
        exit $ERRORS{'UNKNOWN'};
};
alarm($timeout);

my ($status, $message) = checkJetstor($hostname, $community, $snmpPort, $snmpVersion, $snmpTimeout, %oids);

print "JETSTOR $status: $message\n";

exit $ERRORS{$status};


#
sub checkJetstor {
  my ($host, $snmpCommunity, $snmpPort, $snmpVersion, $snmpTimeout, $oids) = @_;

  my ($message, $status);

  my ($session) = new SNMP::Session(
                                    DestHost => $hostname,
                                    Community => $snmpCommunity,
                                    RemotePort => $snmpPort,
                                    Version => $snmpVersion,
                                    Timeout => $snmpTimeout,
                                   );

  if (!defined($session)) {
    return('UNKNOWN', "Failed to connect to $hostname");
  }

  # First we check to see if it's a 416F/516FF
  ($status, $message) = checkType($session, $oids, "checkFiber");

  if (defined($status)) {
    return($status, $message);
  }

  # Next we check to see if it's a 416iS
  ($status, $message) = checkType($session, $oids, "checkiSCSI");

  if (defined($status)) {
    return($status, $message);
  }

  return ('UNKNOWN', "Unknown device type");
}


#
sub checkType {
  my ($session, $oids, $type) = @_;

  # 
  my %validRoutines = (
                       checkFiber => \&checkFiber,
                       checkiSCSI => \&checkiSCSI,
                      );

  my $result = $session->get($oids{$type});

  if (defined($result) && $result ne "" && $result ne "NOSUCHOBJECT") {

    $result =~ s/^\s+//;
    $result =~ s/\s+$//;

    return(&{$validRoutines{$type}}($session, $result, $oids));
  }

  return(undef, undef);
}


#
sub checkFiber {
  my ($session, $model, $oids) = @_;

  my ($status, $message) = ("OK", "");

  my ($psStatuses, $fanSpeeds, $hddTemps, $volumeNames, $volumeStatuses) =
    $session->bulkwalk( 0, 16, [[$oids{fiberPSStatuses}], [$oids{fiberFanSpeeds}],
                                [$oids{fiberHDDTemps}], [$oids{fiberVolumeNames}],
                                [$oids{fiberVolumeStatuses}]]);

  if (!defined($psStatuses)) {

    $message = appendMsg($message, "No PS Info");
    $status = 'CRITICAL';

  } else {

    my $i=0;
    my $failure=0;

    while (defined($$psStatuses[$i])) {

      if ($$psStatuses[$i]->val != 1) {

	$message = appendMsg($message, "PS #$i BAD");
	$status = 'CRITICAL';
	$failure = 1;
      }

      $i++;
    }

    if (!$failure) {
      $message = appendMsg($message, "$i PS's OK");
    }
  }

  if (!defined($fanSpeeds)) {

    $message = appendMsg($message, "No Fan Info");
    $status = 'CRITICAL';

  } else {

    my $i = 0;
    my $failure=0;

    while (defined($$fanSpeeds[$i])) {

      if ($$fanSpeeds[$i]->val <= 1000 || $$fanSpeeds[$i]->val >= 5000) {

        $message = appendMsg($message, "Fan #$i BAD (RPM=" . $$fanSpeeds[$i]->val . ")");
        $status = 'CRITICAL';
        $failure = 1;
      }

      $i++;
    }

    if (!$failure) {
      $message = appendMsg($message, "$i Fan's OK");
    }
  }

  if (!defined($hddTemps)) {

    $message = appendMsg($message, "No HDD Info");
    $status = 'CRITICAL';

  } else {

    my $i = 0;
    my $failure=0;

    while (defined($$hddTemps[$i])) {

      if ($$hddTemps[$i]->val >= 40 && $$hddTemps[$i]->val < 50) {

        $message = appendMsg($message, "HDD #$i Warning (Temp=" . $$hddTemps[$i]->val . "C)");

        if ($status ne 'CRITICAL') {
          $status = 'WARNING';
        }

        $failure = 1;

      } elsif ($$hddTemps[$i]->val >= 50) {

        $message = appendMsg($message, "HDD #$i Critical Temp (" . $$hddTemps[$i]->val . "C)");
        $status = 'CRITICAL';
        $failure = 1;
      }

      $i++;
    }

    if (!$failure) {
      $message = appendMsg($message, "$i HDD Temp's OK");
    }
  }

  if (!defined($volumeStatuses)) {

    $message = appendMsg($message, "No Volume Info");
    $status = 'CRITICAL';

  } else {

    my $i = 0;
    my $failure=0;

    while (defined($$volumeStatuses[$i])) {

      if ($$volumeStatuses[$i]->val ne "Normal") {

        my $name = $$volumeNames[$i]->val;
        $name =~ s/^\s+//;
        $name =~ s/\s+$//;
        $message = appendMsg($message, "Volume $name BAD (State=" . $$volumeStatuses[$i]->val . ")");
        $status = 'CRITICAL';
        $failure = 1;

      }

      $i++;
    }

    if (!$failure) {
      $message = appendMsg($message, "$i Volume's OK");
    }
  }

  return($status, "$model: $message");
}


#
sub checkiSCSI {
  my ($session, $model, $oids) = @_;

  my ($status, $message) = ("OK", "");

  # We start out by checking the harddrives
  my ($udvNames, $udvStatuses) = $session->bulkwalk( 0, 17, [[$oids{iSCSIudvNames}], [$oids{iSCSIudvStatuses}]]);

  if (!defined($udvNames) || !defined($udvStatuses)) {

    $message = appendMsg($message, "Can't retrieve UDV info");
    $status = 'CRITICAL';

  } else {

    my $i = 0;
    my $failure = 0;

    while (defined($$udvStatuses[$i])) {

      if ($$udvStatuses[$i]->val !~ /^Online/) {

        my $name = $$udvNames[$i]->val;
        $name =~ s/^\s+//;
        $name =~ s/\s+$//;
        $message = appendMsg($message, "UDV $name " . $$udvStatuses[$i]->val);
        $status = 'CRITICAL';
        $failure = 1;
      }

      $i++;
    }

    if (!$failure) {
      $message = appendMsg($message, "$i UDV's OK");
    }
  }

  my ($emsNames) = $session->bulkwalk( 0, 17, [[$oids{iSCSIemsNames}]]);

  if (!defined($emsNames)) {

    $message = appendMsg($message, "Can't retrieve enclosure info");
    $status = 'CRITICAL';

  } else {

    my $noPSUs = 0;
    my $noFANs = 0;

    my $i = 0;

    while (defined($$emsNames[$i])) {

      if ($$emsNames[$i]->val =~ /^(PSU\d+\S*)/) {

        my $PSUname = $1;

        $noPSUs++;

        my ($PSUstatus) = $session->get($oids{iSCSIpsuStatus} . substr($$emsNames[$i][0], rindex($$emsNames[$i][0],".")));

	if (!defined($PSUstatus)) {

	  $message = appendMsg($message, "Can't PSU status");
	  $status = 'CRITICAL';

	} else {

	  if ($PSUstatus !~ /^good/) {

	    $message = appendMsg($message, "$PSUname $PSUstatus");
	    $status = 'CRITICAL';
	    $noPSUs = -99999;
	  }
        }

      } elsif ($$emsNames[$i]->val =~ /^(FAN\d+\S*)/) {

        my $FANname = $1;

        $noFANs++;

        my ($FANstatus) = $session->get($oids{iSCSIfanStatus} . substr($$emsNames[$i][0], rindex($$emsNames[$i][0],".")));

	if (!defined($FANstatus)) {

	  $message = appendMsg($message, "Can't Fan status");
	  $status = 'CRITICAL';

	} else {

	  if ($FANstatus !~ /^good/) {

	    $message = appendMsg($message, "$FANname $FANstatus");
	    $status = 'CRITICAL';
	    $noFANs = -99999;
	  }
        }
      }
      $i++;
    }

    if ($noPSUs > 0) {
      $message = appendMsg($message, "$noPSUs PSU's OK");
    }

    if ($noFANs > 0) {
      $message = appendMsg($message, "$noFANs Fan's OK");
    }
  }

  return($status, "$model: $message");
}


#
sub checkValues {

  my ($array, $warning, $warningMsg, $critical, $criticalMsg, $message, $status, $okMsg) = @_;

  return;
}


#
sub print_usage {
  print "Usage: $PROGNAME -H <host> [-c <community>] [-h] [-V]\n";
}


#
sub appendMsg {
  my ($orig, $new) = @_;

  $orig .= ", " if (defined($orig) && $orig ne "");

  $orig .= $new;

  return($orig);
}
