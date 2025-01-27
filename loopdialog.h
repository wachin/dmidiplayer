/*
    Drumstick MIDI File Player Multiplatform Program
    Copyright (C) 2006-2022, Pedro Lopez-Cabanillas <plcl@users.sf.net>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef LOOPDIALOG_H
#define LOOPDIALOG_H

#include <QDialog>

namespace Ui {
    class LoopDialog;
}

class LoopDialog : public QDialog
{
    Q_OBJECT

public:
    explicit LoopDialog(QWidget *parent = nullptr);
    ~LoopDialog();
    int getFromBar();
    int getToBar();

public slots:
    void setLastBar(int bar);
    void initValues(int from, int to);
    void accept() override;

private:
    Ui::LoopDialog *m_ui;
};

#endif // LOOPDIALOG_H
