#mkdir /root/.pytigon
mkdir /root/.pytigon/ext_prg
curl -L -o /root/.pytigon/ext_prg/tcc-0.9.26.tar.bz2 http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.26.tar.bz2
tar xjf /root/.pytigon/ext_prg/tcc-0.9.26.tar.bz2 -C /root/.pytigon/ext_prg/
rm /root/.pytigon/ext_prg/tcc-0.9.26.tar.bz2
mv /root/.pytigon/ext_prg/tcc-0.9.26 /root/.pytigon/ext_prg/tcc
cd /root/.pytigon/ext_prg/tcc
./configure --disable-static
make
